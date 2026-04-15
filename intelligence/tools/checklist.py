from .fill import (
    fill_initial_case_details,
    fill_basic_kyc_sections,
    update_checklist_with_verification_results,
    fill_financial_sections,
    fill_nationality,
    fill_pan_validation,
    fill_aadhaar_validation,
    fill_address_proof,
    fill_photo_validation,
    fill_bank_validation,
    fill_occupation,
    fill_education,
    fill_nominee,
)


def run_step_final_checklist_update(agent):
    """Step 7: The Master Fill. Consolidates all gathered data into one comprehensive checklist update pass."""
    agent.state.set_step("Master Checklist Fill", "Underwriting App - Complete")
    agent.state.set_progress(0.90)
    agent.state.log("🚀 Starting Master Checklist Fill (All-In-One pass)...", "info")

    try:
        # Navigate to underwriting app
        app_url = f"{agent.underwriting_url}/{agent.application_no}"
        agent.page.goto(app_url)
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        agent.ui.wait(1.0)

        # 1. Fill Initial Case Details (Card 1)
        fill_initial_case_details(agent)

        # 2. Update Checklist with Verification Results (Card 2: KYC/Documents)
        update_checklist_with_verification_results(agent)

        # 3. Fill Final Financial Sections (Card 3: Occupation/Income/Min Balance)
        fill_financial_sections(agent)

        agent.state.log("✅ Master Checklist Fill completed successfully", "success")

    except Exception as e:
        agent.state.log(f"❌ Master Checklist Fill failed: {e}", "error")
        raise


def find_and_click_document(agent, selector: str, doc_type: str) -> bool:
    """Try to find and click on a document using various selectors."""
    selectors = [
        selector,
        f"img[alt*='{doc_type}']",
        f"img[src*='{doc_type}']",
        f".{doc_type}-document",
        f"#{doc_type}-doc",
        f"button:has-text('{doc_type}')",
        f"a:has-text('{doc_type}')",
    ]

    for sel in selectors:
        try:
            element = agent.page.query_selector(sel)
            if element:
                element.click()
                agent.ui.wait(0.5)
                return True
        except Exception:
            continue

    return False


def run_step_fill_case_details(agent):
    """Step 2: Navigate to UW checklist and fill Card 1 via Playwright."""
    agent.state.set_step("Filling Case Details", "Card 1")
    agent.state.set_progress(0.15)
    agent.state.log("📝 Opening Underwriting Checklist...", "info")

    app_url = f"{agent.underwriting_url}/{agent.application_no}"
    agent.page.goto(app_url)
    agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
    agent.ui.wait(0.5)

    screenshot = agent.ui.screenshot()
    agent.state.add_screenshot("Underwriting Checklist - Opened", screenshot)

    data = agent._applicant_data
    agent.state.log("📝 Filling Card 1: Case Details...", "info")

    agent.ui.scroll_to("card1")
    agent.ui.fill_text(
        "input_application_no",
        data.get("app_no", data.get("application_no", "OS121345678")),
        "Application No",
    )
    agent.ui.select("input_case_type", data.get("case_type", "AMR"), "Case Type")
    agent.ui.select(
        "input_sourcing_channel", data.get("sourcing_type", "FR"), "Sourcing Channel"
    )
    agent.ui.select("input_proposed_status", "LA", "Proposed Status")
    agent.ui.select("input_gender_la", data.get("gender", "Male"), "Gender of LA")

    screenshot = agent.ui.screenshot()
    agent.state.add_screenshot("Card 1 - Case Details Filled", screenshot)
    agent.state.log("✅ Card 1: Case Details filled", "success")
    agent.state.set_progress(0.20)
    agent.ui.wait(0.3)


def run_step_fill_kyc_sections(agent):
    """Step 3: Fill all KYC sections in Card 2 via REST API (no waits between clicks)."""
    data = agent._applicant_data

    fill_nationality(agent, data)
    if not agent.state.running:
        return

    fill_pan_validation(agent, data)
    if not agent.state.running:
        return

    fill_aadhaar_validation(agent, data)
    if not agent.state.running:
        return

    fill_address_proof(agent, data)
    if not agent.state.running:
        return

    # Section 5: Photo Validation
    fill_photo_validation(agent, data)
    if not agent.state.running:
        return

    # Section 6: Bank Validation
    fill_bank_validation(agent, data)


def run_step_fill_financial_sections(agent):
    """Step 4: Fill Card 3 - Financial sections."""
    data = agent._applicant_data

    # Occupation
    fill_occupation(agent, data)
    if not agent.state.running:
        return

    # Education
    fill_education(agent, data)
    if not agent.state.running:
        return

    # Nominee
    fill_nominee(agent, data)
