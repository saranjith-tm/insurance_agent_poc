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
# (used by dashboard/Home.py — independent of the underwriting agent)
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


def _extract_field_value(field):
    """Recursively extract the value from an Azure DocumentField."""
    if not field:
        return ""
        
    field_type = getattr(field, "type", getattr(field, "value_type", None))
    
    if field_type == "array":
        arr = getattr(field, "value_array", getattr(field, "value", []))
        return [_extract_field_value(item) for item in (arr or [])]
    elif field_type == "object":
        obj = getattr(field, "value_object", getattr(field, "value", {}))
        return {k: _extract_field_value(v) for k, v in (obj or {}).items()}
    else:
        val = field.content if hasattr(field, "content") else getattr(field, "value", None)
        return val if val is not None else ""


def extract_document_fields(
    file_bytes: bytes,
    filename: str,
    azure_endpoint: str,
    azure_key: str,
    azure_model_id: str = "prebuilt-document",
    progress_callback=None,
):
    """Extract all fields from an uploaded document using Azure Document Intelligence.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the uploaded file.
    filename : str
        Original filename — used to detect the '.pdf' extension.
    azure_endpoint : str
        Azure Document Intelligence Endpoint.
    azure_key : str
        Azure Document Intelligence API Key.
    azure_model_id : str
        Custom model ID, defaults to 'prebuilt-document'.
    progress_callback : callable(current_page: int, total_pages: int), optional
        Called to update a UI progress indicator.

    Returns
    -------
    tuple:
        merged_data        : dict   — extracted key-value pairs
        page_images        : list   — list[bytes] PNG per page for UI
        avg_confidence     : float  — average extraction_confidence
        total_input_tokens : int    — 0 (not applicable for Azure)
        total_output_tokens: int    — 0 (not applicable for Azure)
        model_id           : str    — 'azure-prebuilt-document'
    """
    from azure.core.credentials import AzureKeyCredential
    from azure.ai.documentintelligence import DocumentIntelligenceClient
    import re

    is_pdf = filename.lower().endswith(".pdf")
    page_images = pdf_to_images(file_bytes) if is_pdf else [file_bytes]

    if progress_callback:
        progress_callback(1, 1)

    content_type = "application/pdf" if is_pdf else "application/octet-stream"

    client = DocumentIntelligenceClient(
        endpoint=azure_endpoint,
        credential=AzureKeyCredential(azure_key)
    )

    poller = client.begin_analyze_document(
        azure_model_id,
        body=file_bytes,
        content_type=content_type
    )
    result = poller.result()

    merged_data = {}
    confidences = []

    # 1. Process Key-Value Pairs (common in prebuilt-document model)
    if hasattr(result, "key_value_pairs") and result.key_value_pairs:
        for kvp in result.key_value_pairs:
            if kvp.key and hasattr(kvp.key, "content") and kvp.value and hasattr(kvp.value, "content"):
                # Normalize key
                key = kvp.key.content.strip().lower()
                key = re.sub(r'[^a-z0-9]+', '_', key).strip('_')
                
                value = kvp.value.content.strip()
                conf = kvp.confidence if hasattr(kvp, "confidence") else 0.95
                confidences.append(conf)
                
                if key not in merged_data or merged_data[key] in ("", None):
                    merged_data[key] = value

    # 2. Process Fields from Documents (common in custom models)
    if hasattr(result, "documents") and result.documents:
        for doc in result.documents:
            if hasattr(doc, "fields") and doc.fields:
                for name, field in doc.fields.items():
                    # Normalize key from the field name
                    key = name.strip().lower()
                    key = re.sub(r'[^a-z0-9]+', '_', key).strip('_')
                    
                    value = _extract_field_value(field)
                    
                    conf = field.confidence if hasattr(field, "confidence") else 0.95
                    confidences.append(conf)
                    
                    if key not in merged_data or merged_data[key] in ("", None):
                        merged_data[key] = value

    avg_confidence = sum(confidences) / len(confidences) if confidences else 1.0
    merged_data["extraction_confidence"] = round(avg_confidence, 4)

    return merged_data, page_images, avg_confidence, 0, 0, f"azure-{azure_model_id}"

