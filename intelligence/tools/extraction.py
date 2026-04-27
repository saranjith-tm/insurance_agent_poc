from .verification import validate_documents_from_sales_agent
import json


def run_step_extract_single_screen_data(agent):
    """Step 2: Extract applicant details from the single screen view."""
    agent.state.set_step(
        "Extracting Single Screen Data", "Sales Agent App - Single Screen"
    )
    agent.state.set_progress(0.08)
    agent.state.log("Extracting applicant data from single screen view...", "info")

    # Navigate to single screen tab
    try:
        agent.page.goto(f"{agent.sales_url}/case/{agent.application_no}/single")
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        agent.ui.wait(1.0)

        # Take screenshot of single screen
        screenshot = agent.ui.screenshot()
        agent.state.add_screenshot("Sales Agent - Single Screen", screenshot)

        # Try API first for structured data
        try:
            import httpx

            resp = httpx.get(
                f"{agent.sales_url}/api/applicant/{agent.application_no}", timeout=10
            )
            if resp.status_code == 200:
                agent._applicant_data = resp.json()
                agent.state.extracted_data = agent._applicant_data
                agent.state.log(
                    f"Applicant data loaded via API: {agent._applicant_data.get('name', 'N/A')} | PAN: {agent._applicant_data.get('pan_no', 'N/A')}",
                    "success",
                )
            else:
                raise Exception("API returned non-200 status")
        except Exception as api_err:
            agent.state.log(
                f"API fetch failed: {api_err} - using VLM extraction", "warning"
            )

            # Use VLM to extract data from screenshot
            if agent.use_visual_mode:
                fields = [
                    "first_name",
                    "last_name",
                    "pan_number",
                    "aadhaar_number",
                    "dob",
                    "occupation",
                    "gender",
                    "annual_income",
                    "bank_account",
                    "ifsc",
                    "nominee_name",
                ]
                extracted, usage = agent.vlm.extract_data(screenshot, fields)
                agent.state.update_usage(usage.input_tokens, usage.output_tokens, usage.model_id)
                agent._applicant_data = extracted
                agent.state.extracted_data = extracted
                agent.state.log(
                    f"VLM extracted data: {json.dumps(extracted)[:200]}...", "info"
                )
            else:
                # Use mock data if VLM is disabled
                agent._applicant_data = {
                    "name": "DEMO APPLICANT",
                    "pan_no": "ABCKS1234K",
                    "aadhaar_no": "123456789012",
                    "dob": "01/01/1990",
                    "gender": "Male",
                    "occupation": "Software Engineer",
                    "annual_income": 1200000,
                    "bank_account": "1234567890",
                    "ifsc": "ICIC0000001",
                }
                agent.state.extracted_data = agent._applicant_data
                agent.state.log("Using demo data (VLM mode disabled)", "warning")

        agent.state.log("Single screen data extraction completed", "success")

    except Exception as e:
        agent.state.log(f"Single screen extraction failed: {e}", "error")
        raise


def run_step_extract_applicant_data(agent):
    """Step 1: Extract applicant data and validate documents from Sales Agent app."""
    agent.state.set_step("Extracting applicant data", "Sales Agent App")
    agent.state.set_progress(0.05)
    agent.state.log("📋 Fetching applicant data from Sales Agent API...", "info")

    # Primary: REST API (instant, structured)
    try:
        import httpx

        resp = httpx.get(
            f"{agent.sales_url}/api/applicant/{agent.application_no}", timeout=10
        )
        if resp.status_code == 200:
            agent._applicant_data = resp.json()
            agent.state.extracted_data = agent._applicant_data
            agent.state.log(
                f"✅ Applicant data loaded: {agent._applicant_data.get('name', 'N/A')} | PAN: {agent._applicant_data.get('pan_no', 'N/A')}",
                "success",
            )
    except Exception as e:
        agent.state.log(f"  API fetch failed: {e} — will rely on VLM", "warning")
        agent._applicant_data = {}

    # Validate documents after getting applicant data
    if agent._applicant_data:
        validate_documents_from_sales_agent(agent)

    # Only call VLM if API failed to get data AND visual mode is on
    if not agent._applicant_data and agent.use_visual_mode:
        agent.page.goto(f"{agent.sales_url}/case/{agent.application_no}/single")
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        screenshot = agent.ui.screenshot()
        agent.state.add_screenshot("Sales Agent - Single Screen", screenshot)
        agent.state.log("🔍 VLM extracting applicant data from screenshot...", "info")
        try:
            fields = [
                "first_name",
                "last_name",
                "pan_number",
                "aadhaar_number",
                "dob",
                "occupation",
            ]
            extracted, usage = agent.vlm.extract_data(screenshot, fields)
            agent.state.update_usage(usage.input_tokens, usage.output_tokens, usage.model_id)
            agent._applicant_data = extracted
            agent.state.extracted_data = extracted
            agent.state.log(f"🤖 VLM extracted: {json.dumps(extracted)[:200]}", "info")
            # Also validate documents if using VLM
            validate_documents_from_sales_agent(agent)
        except Exception as e:
            agent.state.log(f"  VLM extraction failed: {e}", "warning")
    else:
        # Take a quick screenshot for the dashboard (no VLM call)
        agent.page.goto(f"{agent.sales_url}/case/{agent.application_no}/single")
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        screenshot = agent.ui.screenshot()
        agent.state.add_screenshot("Sales Agent - Single Screen", screenshot)

    agent.state.set_progress(0.12)
    agent.ui.wait(0.3)


# ---------------------------------------------------------------------------
# Dashboard document extraction helpers
# (used by dashboard/app.py — independent of the underwriting agent)
# ---------------------------------------------------------------------------

def pdf_to_images(pdf_bytes: bytes, dpi: int = 200) -> list:
    """Render every page of a PDF to PNG bytes using PyMuPDF.

    Returns a list of bytes objects, one PNG per page.
    Requires: pymupdf >= 1.24  (pip install pymupdf)
    """
    try:
        import pymupdf as fitz  # PyMuPDF >= 1.24
    except ImportError:
        import fitz  # older PyMuPDF

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pages = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat, alpha=False)
        pages.append(pix.tobytes("png"))
    doc.close()
    return pages


def merge_extracted_data(base: dict, update: dict) -> dict:
    """Deep-merge two extracted JSON dicts from consecutive VLM calls.

    Rules:
    - 'extraction_confidence' is skipped (caller handles it separately).
    - Scalar values: only overwrite if the existing value is empty / None.
    - List values: concatenate.
    """
    result = dict(base)
    for k, v in update.items():
        if k == "extraction_confidence":
            continue
        if k not in result or result[k] in ("", None):
            result[k] = v
        elif isinstance(result[k], list) and isinstance(v, list):
            result[k] = result[k] + v
    return result


def extract_document_fields(
    file_bytes: bytes,
    filename: str,
    vlm_client,
    prompt: str,
    progress_callback=None,
):
    """Extract all fields from an uploaded document (image or PDF).

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the uploaded file.
    filename : str
        Original filename — used to detect the '.pdf' extension.
    vlm_client :
        An initialised VLM client (from intelligence.helpers.get_vlm_client).
    prompt : str
        System prompt sent to the VLM for every page.
    progress_callback : callable(current_page: int, total_pages: int), optional
        Called before each page is processed so the caller can update a UI
        progress indicator.

    Returns
    -------
    tuple:
        merged_data        : dict   — extracted fields merged across all pages
        page_images        : list   — list[bytes] PNG per page
        avg_confidence     : float  — average extraction_confidence
        total_input_tokens : int
        total_output_tokens: int
        model_id           : str
    """
    is_pdf = filename.lower().endswith(".pdf")
    page_images = pdf_to_images(file_bytes) if is_pdf else [file_bytes]

    total_pages = len(page_images)
    merged_data: dict = {}
    total_input = 0
    total_output = 0
    confidences = []
    last_usage = None

    for idx, img_bytes in enumerate(page_images):
        if progress_callback:
            progress_callback(idx + 1, total_pages)

        page_data, usage = vlm_client.analyze_document(img_bytes, prompt)
        total_input += usage.input_tokens
        total_output += usage.output_tokens
        last_usage = usage

        conf = float(page_data.get("extraction_confidence", 0.95))
        confidences.append(conf)
        merged_data = merge_extracted_data(merged_data, page_data)

    avg_confidence = sum(confidences) / len(confidences)
    merged_data["extraction_confidence"] = round(avg_confidence, 4)

    model_id = last_usage.model_id if last_usage else ""
    return merged_data, page_images, avg_confidence, total_input, total_output, model_id

