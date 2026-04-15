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
                extracted = agent.vlm.extract_data(screenshot, fields)
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
            extracted = agent.vlm.extract_data(screenshot, fields)
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
