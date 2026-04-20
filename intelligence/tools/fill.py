def fill_initial_case_details(agent):
    """Fill basic case details without document validation."""
    data = agent._applicant_data
    agent.state.log("Filling initial case details...", "info")

    agent.ui.scroll_to("card1")
    agent.ui.fill_text(
        "input_application_no",
        data.get("app_no", data.get("application_no", agent.application_no)),
        "Application No",
    )
    agent.ui.select("input_case_type", data.get("case_type", "AMR"), "Case Type")
    agent.ui.select(
        "input_sourcing_channel", data.get("sourcing_type", "FR"), "Sourcing Channel"
    )
    agent.ui.select("input_proposed_status", "LA", "Proposed Status")
    agent.ui.select("input_gender_la", data.get("gender", "Male"), "Gender of LA")


def fill_basic_kyc_sections(agent):
    """Fill basic KYC sections that don't require document verification."""
    data = agent._applicant_data
    # Fill nationality (Step 3: Initial pass)
    fill_nationality(agent, data)


def update_checklist_with_verification_results(agent):
    """Update checklist fields based on REAL document verification results from Step 5."""
    agent.state.log("🎯 Applying verified document results to checklist...", "info")
    data = agent._applicant_data
    val = agent._document_validation
    val_details = val.get("validation_details", {})
    doc_confidences = agent.state.doc_confidences

    # Helper to find document metrics by substring (e.g. "AADHAAR")
    def get_doc_metrics(doc_type_substring):
        for tab_name, details in val_details.items():
            if doc_type_substring in details.get("doc_type", "").upper():
                conf = doc_confidences.get(tab_name, 0.0)
                is_valid = details.get("valid", False)
                ext_id = details.get("extracted_id")
                return {"found": True, "conf": conf, "valid": is_valid, "extracted_id": ext_id}
        return {"found": False, "conf": 0.0, "valid": False, "extracted_id": None}

    pan_metrics = get_doc_metrics("PAN")
    aadhaar_metrics = get_doc_metrics("AADHAAR")
    bank_metrics = get_doc_metrics("BANK")
    photo_metrics = get_doc_metrics("PROPOSAL")

    # --- Section: PAN Validation ---
    agent.ui.scroll_to("sec-pan")
    pan_uploaded = pan_metrics["conf"] >= 0.1
    pan_clear = pan_metrics["conf"] >= 0.50
    pan_matches = pan_metrics["valid"]

    agent.ui.click_yn("pan_copy_uploaded", pan_uploaded, "PAN Card Copy uploaded")
    agent.ui.click_yn("pan_copy_clear", pan_clear, "PAN Card Copy is clear and legible")
    agent.ui.click_yn("dob_matches_iuw", pan_matches, f"DOB matches IUW ({data.get('dob', 'N/A')})")
    
    pan_no = pan_metrics.get("extracted_id") or data.get("pan_no") or data.get("pan_number", "")
    agent.ui.api_fill("pan_number_entered", pan_no, f"PAN Number = '{pan_no}'")

    # --- Section: Aadhaar Validation ---
    agent.ui.scroll_to("sec-aadhaar")
    aad_uploaded = aadhaar_metrics["conf"] >= 0.1
    aad_clear = aadhaar_metrics["conf"] >= 0.50
    aad_matches = aadhaar_metrics["valid"]

    agent.ui.click_yn("aadhaar_copy_uploaded", aad_uploaded, "Aadhaar Card Copy uploaded")
    agent.ui.click_yn("aadhaar_copy_clear", aad_clear, "Aadhaar Card Copy is clear and legible")
    agent.ui.click_yn("aadhaar_name_matches", aad_matches, "Name matches Aadhaar card")
    agent.ui.click_yn("aadhaar_dob_matches", aad_matches, "DOB matches Aadhaar card")
    
    aad_no = aadhaar_metrics.get("extracted_id") or data.get("aadhaar_no") or data.get("aadhaar_number", "")
    
    # Mask Aadhaar for privacy (like the old code did before it was removed)
    if aad_no and len(str(aad_no).replace(" ", "")) >= 12:
        clean_aad = str(aad_no).replace(" ", "")
        masked = f"XXXX XXXX {clean_aad[-4:]}"
    else:
        masked = aad_no
        
    agent.ui.api_fill("aadhaar_number_entered", masked, f"Aadhaar Number = '{masked}'")

    # --- Section: Address Proof ---
    agent.ui.scroll_to("sec-address")
    address_uploaded = aad_uploaded or (bank_metrics["conf"] >= 0.1)
    address_clear = aad_clear or (bank_metrics["conf"] >= 0.50)
    address_matches = aad_matches or bank_metrics["valid"]

    agent.ui.click_yn("address_doc_uploaded", address_uploaded, "Address document uploaded")
    agent.ui.click_yn("address_doc_clear", address_clear, "Address document is clear")
    agent.ui.click_yn("address_matches_iuw", address_matches, "Address matches IUW")

    # --- Section: Photo Validation ---
    agent.ui.scroll_to("sec-photo")
    photo_uploaded = photo_metrics["conf"] >= 0.1
    photo_clear = photo_metrics["conf"] >= 0.50
    photo_matches = photo_metrics["valid"]

    agent.ui.click_yn("photo_uploaded", photo_uploaded, "Applicant photo uploaded")
    agent.ui.click_yn("photo_clear", photo_clear, "Photo is clear and recognizable")
    agent.ui.click_yn("face_matches_id", photo_matches, "Face matches ID document")

    # --- Section: Bank Validation ---
    agent.ui.scroll_to("sec-bank")
    bank_uploaded = bank_metrics["conf"] >= 0.1
    bank_matches = bank_metrics["valid"]

    agent.ui.click_yn("bank_statement_uploaded", bank_uploaded, "Bank statement uploaded")
    agent.ui.click_yn("account_no_matches", bank_matches, "Account number matches")
    agent.ui.click_yn("name_on_statement_matches", bank_matches, "Name on statement matches")

    # Fill bank text details
    agent.ui.api_fill("account_number_entered", data.get("bank_account", ""), "Account Number")
    agent.ui.api_fill("ifsc_entered", data.get("ifsc", ""), "IFSC Code")


def fill_financial_sections(agent):
    """Fill the remaining financial sections."""
    data = agent._applicant_data

    # Occupation section
    agent.ui.scroll_to("sec-occupation")
    agent.ui.select(
        "input_occupation", data.get("occupation", "Software Engineer"), "Occupation"
    )
    agent.ui.select(
        "input_industry_type",
        data.get("industry", "Information Technology"),
        "Industry Type",
    )
    agent.ui.click_yn("is_hazardous", False, "Is hazardous occupation")

    # Minimum Balance (Extracted from Bank Statement)
    min_balance = data.get("minimum_balance")
    if min_balance and min_balance not in ["Not Found", "Error"]:
        agent.ui.scroll_to("sec-income")
        agent.ui.fill_text("input_minimum_balance", min_balance, "Minimum Balance")

    # Education section
    agent.ui.scroll_to("sec-education")
    agent.ui.select(
        "input_education_level", data.get("education", "Graduate"), "Education Level"
    )

    # Nominee section
    agent.ui.scroll_to("sec-nominee")
    agent.ui.click_yn("nominee_details_added", True, "Nominee details added")


def fill_nationality(agent, data: dict):
    """Fill nationality/resident status section via Playwright."""
    agent.state.set_step("Filling Nationality Section", "Card 2: KYC")
    agent.state.set_progress(0.25)
    agent.state.log("🌍 Filling Nationality / Resident Status...", "info")

    agent.ui.scroll_to("sec-nationality")
    mapping = {
        "NRI": "NRI",
        "Resident": "Resident Indian",
        "Resident Indian": "Resident Indian",
        "PIO": "PIO",
        "Foreign National": "Foreign National",
    }
    select_value = mapping.get(data.get("resident_status", "NRI"), "NRI")
    agent.ui.select("input_declared_residence_iuw", select_value, "Declared Residence")

    agent.state.log("✅ Nationality section filled", "success")


def fill_pan_validation(agent, data: dict):
    """Fill PAN validation section using validation results from sales agent app."""
    agent.state.set_step("Filling PAN Validation", "Card 2: KYC - PAN")
    agent.state.set_progress(0.32)
    agent.state.log("💳 Filling PAN Validation section...", "info")

    # Check validation results from sales agent app
    pan_valid = getattr(agent, "_document_validation", {}).get("pan_valid", True)
    pan_details = (
        getattr(agent, "_document_validation", {})
        .get("validation_details", {})
        .get("pan", {})
    )

    agent.ui.scroll_to("sec-pan")

    # Use validation results to determine selections
    if pan_valid:
        agent.ui.click_yn("pan_copy_uploaded", True, "PAN Card Copy uploaded")
        agent.ui.click_yn("pan_copy_clear", True, "PAN Card Copy is clear and legible")
        agent.ui.click_yn(
            "dob_matches_iuw", True, f"DOB matches IUW ({data.get('dob', 'N/A')})"
        )
        agent.state.log(
            "✅ PAN document validated - marking as uploaded and clear", "info"
        )
    else:
        # If validation failed, still mark as uploaded but note issues
        agent.ui.click_yn("pan_copy_uploaded", True, "PAN Card Copy uploaded")
        issues = pan_details.get("issues", [])
        if "unclear" in issues or "unreadable" in issues:
            agent.ui.click_yn(
                "pan_copy_clear", False, "PAN Card Copy is clear and legible"
            )
            agent.state.log("⚠️ PAN document has clarity issues", "warning")
        else:
            agent.ui.click_yn(
                "pan_copy_clear", True, "PAN Card Copy is clear and legible"
            )

        if "name_mismatch" in issues:
            agent.ui.click_yn(
                "dob_matches_iuw", False, f"DOB matches IUW ({data.get('dob', 'N/A')})"
            )
            agent.state.log("⚠️ PAN document has data mismatches", "warning")
        else:
            agent.ui.click_yn(
                "dob_matches_iuw", True, f"DOB matches IUW ({data.get('dob', 'N/A')})"
            )

    # Extract PAN number from validation results if available
    extracted_pan = pan_details.get("extracted_data", {}).get(
        "pan_number", data.get("pan_no", "")
    )
    agent.ui.fill_text("input_pan_number_entered", extracted_pan, "PAN Number")

    screenshot = agent.ui.screenshot()
    agent.state.add_screenshot("Card 2 - PAN Validation", screenshot)
    agent.state.log("✅ PAN Validation section filled", "success")


def fill_aadhaar_validation(agent, data: dict):
    """Fill Aadhaar validation section using validation results from sales agent app."""
    agent.state.set_step("Filling Aadhaar Validation", "Card 2: KYC - Aadhaar")
    agent.state.set_progress(0.44)
    agent.state.log("🪪 Filling Aadhaar Validation section...", "info")

    # Check validation results from sales agent app
    aadhaar_valid = getattr(agent, "_document_validation", {}).get(
        "aadhaar_valid", True
    )
    aadhaar_details = (
        getattr(agent, "_document_validation", {})
        .get("validation_details", {})
        .get("aadhaar", {})
    )

    agent.ui.scroll_to("sec-aadhaar")

    # Use validation results to determine selections
    if aadhaar_valid:
        agent.ui.click_yn("aadhaar_copy_uploaded", True, "Aadhaar copy uploaded")
        agent.ui.click_yn(
            "aadhaar_copy_clear", True, "Aadhaar copy is clear and legible"
        )
        agent.ui.click_yn(
            "aadhaar_name_matches",
            True,
            f"Name on Aadhaar matches IUW ({data.get('name', 'N/A')})",
        )
        agent.ui.click_yn(
            "aadhaar_dob_matches",
            True,
            f"DOB on Aadhaar matches IUW ({data.get('dob', 'N/A')})",
        )
        agent.state.log(
            "✅ Aadhaar document validated - marking all checks as passed", "info"
        )
    else:
        # If validation failed, handle issues appropriately
        agent.ui.click_yn("aadhaar_copy_uploaded", True, "Aadhaar copy uploaded")
        issues = aadhaar_details.get("issues", [])

        if "unclear" in issues or "unreadable" in issues:
            agent.ui.click_yn(
                "aadhaar_copy_clear", False, "Aadhaar copy is clear and legible"
            )
            agent.state.log("⚠️ Aadhaar document has clarity issues", "warning")
        else:
            agent.ui.click_yn(
                "aadhaar_copy_clear", True, "Aadhaar copy is clear and legible"
            )

        if "name_mismatch" in issues:
            agent.ui.click_yn(
                "aadhaar_name_matches",
                False,
                f"Name on Aadhaar matches IUW ({data.get('name', 'N/A')})",
            )
            agent.state.log("⚠️ Aadhaar document name mismatch detected", "warning")
        else:
            agent.ui.click_yn(
                "aadhaar_name_matches",
                True,
                f"Name on Aadhaar matches IUW ({data.get('name', 'N/A')})",
            )

        if "dob_mismatch" in issues:
            agent.ui.click_yn(
                "aadhaar_dob_matches",
                False,
                f"DOB on Aadhaar matches IUW ({data.get('dob', 'N/A')})",
            )
            agent.state.log("⚠️ Aadhaar document DOB mismatch detected", "warning")
        else:
            agent.ui.click_yn(
                "aadhaar_dob_matches",
                True,
                f"DOB on Aadhaar matches IUW ({data.get('dob', 'N/A')})",
            )

    # Extract Aadhaar number from validation results if available
    extracted_aadhaar = aadhaar_details.get("extracted_data", {}).get(
        "aadhaar_number", data.get("aadhaar_no", "")
    )
    # Mask first 8 digits per UIDAI guidelines before entering
    parts = extracted_aadhaar.split(" ")
    masked = f"XXXX XXXX {parts[2]}" if len(parts) == 3 else extracted_aadhaar
    agent.ui.fill_text("input_aadhaar_number_entered", masked, "Aadhaar No (masked)")

    screenshot = agent.ui.screenshot()
    agent.state.add_screenshot("Card 2 - Aadhaar Validation", screenshot)
    agent.state.log("✅ Aadhaar Validation section filled", "success")


def fill_address_proof(agent, data: dict):
    """Fill address proof validation section using validation results from sales agent app."""
    agent.state.set_step("Filling Address Proof", "Card 2: KYC - Address")
    agent.state.set_progress(0.54)
    agent.state.log("🏠 Filling Address Proof section...", "info")

    # Check validation results from sales agent app
    address_valid = getattr(agent, "_document_validation", {}).get(
        "bank_statement_valid", True
    )  # Using bank_statement as proxy for address
    address_details = (
        getattr(agent, "_document_validation", {})
        .get("validation_details", {})
        .get("bank_statement", {})
    )

    agent.ui.scroll_to("sec-address")

    # Use validation results to determine selections
    if address_valid:
        agent.ui.click_yn(
            "address_doc_uploaded", True, "Address proof document uploaded"
        )
        agent.ui.click_yn("address_doc_clear", True, "Address proof document is clear")
        agent.ui.click_yn(
            "address_matches_iuw",
            True,
            f"Address matches IUW: {data.get('address1', 'N/A')}, {data.get('city', '')}",
        )
        agent.state.log(
            "✅ Address proof document validated - marking all checks as passed", "info"
        )
    else:
        # If validation failed, handle issues appropriately
        agent.ui.click_yn(
            "address_doc_uploaded", True, "Address proof document uploaded"
        )
        issues = address_details.get("issues", [])

        if "unclear" in issues or "unreadable" in issues:
            agent.ui.click_yn(
                "address_doc_clear", False, "Address proof document is clear"
            )
            agent.state.log("⚠️ Address proof document has clarity issues", "warning")
        else:
            agent.ui.click_yn(
                "address_doc_clear", True, "Address proof document is clear"
            )

        if "address_mismatch" in issues:
            agent.ui.click_yn(
                "address_matches_iuw",
                False,
                f"Address matches IUW: {data.get('address1', 'N/A')}, {data.get('city', '')}",
            )
            agent.state.log(
                "⚠️ Address proof document address mismatch detected", "warning"
            )
        else:
            agent.ui.click_yn(
                "address_matches_iuw",
                True,
                f"Address matches IUW: {data.get('address1', 'N/A')}, {data.get('city', '')}",
            )

    agent.state.log("✅ Address Proof section filled", "success")


def fill_photo_validation(agent, data: dict):
    """Fill photo validation section using validation results from sales agent app."""
    agent.state.set_step("Filling Photo Validation", "Card 2: KYC - Photo")
    agent.state.set_progress(0.62)
    agent.state.log("📸 Filling Photo Validation section...", "info")

    # Check validation results from sales agent app
    photo_valid = getattr(agent, "_document_validation", {}).get(
        "proposal_valid", True
    )  # Using proposal as proxy for photo
    photo_details = (
        getattr(agent, "_document_validation", {})
        .get("validation_details", {})
        .get("proposal", {})
    )

    agent.ui.scroll_to("sec-photo")

    # Use validation results to determine selections
    if photo_valid:
        agent.ui.click_yn("photo_uploaded", True, "Applicant photo uploaded")
        agent.ui.click_yn("photo_clear", True, "Photo is clear and recognizable")
        agent.ui.click_yn("face_matches_id", True, "Face in photo matches ID document")
        agent.state.log(
            "✅ Applicant photo validated - marking all checks as passed", "info"
        )
    else:
        # If validation failed, handle issues appropriately
        agent.ui.click_yn("photo_uploaded", True, "Applicant photo uploaded")
        issues = photo_details.get("issues", [])

        if "unclear" in issues or "blurry" in issues:
            agent.ui.click_yn("photo_clear", False, "Photo is clear and recognizable")
            agent.state.log("⚠️ Applicant photo has clarity issues", "warning")
        else:
            agent.ui.click_yn("photo_clear", True, "Photo is clear and recognizable")

        if "face_mismatch" in issues or "no_face" in issues:
            agent.ui.click_yn(
                "face_matches_id", False, "Face in photo matches ID document"
            )
            agent.state.log("⚠️ Applicant photo face mismatch detected", "warning")
        else:
            agent.ui.click_yn(
                "face_matches_id", True, "Face in photo matches ID document"
            )

    agent.state.log("✅ Photo Validation section filled", "success")


def fill_bank_validation(agent, data: dict):
    """Fill bank account validation section using validation results from sales agent app."""
    agent.state.set_step("Filling Bank Validation", "Card 2: KYC - Bank")
    agent.state.set_progress(0.72)
    agent.state.log("🏦 Filling Bank Account Validation section...", "info")

    # Check validation results from sales agent app
    bank_valid = getattr(agent, "_document_validation", {}).get(
        "bank_statement_valid", True
    )
    bank_details = (
        getattr(agent, "_document_validation", {})
        .get("validation_details", {})
        .get("bank_statement", {})
    )

    agent.ui.scroll_to("sec-bank")

    # Use validation results to determine selections
    if bank_valid:
        agent.ui.click_yn("bank_statement_uploaded", True, "Bank statement uploaded")
        agent.ui.click_yn(
            "account_no_matches",
            True,
            f"Account no matches IUW: {data.get('bank_account', 'N/A')}",
        )
        agent.ui.click_yn(
            "name_on_statement_matches",
            True,
            f"Name on statement matches: {data.get('name', 'N/A')}",
        )
        agent.state.log(
            "✅ Bank statement validated - marking all checks as passed", "info"
        )
    else:
        # If validation failed, handle issues appropriately
        agent.ui.click_yn("bank_statement_uploaded", True, "Bank statement uploaded")
        issues = bank_details.get("issues", [])

        if "account_mismatch" in issues:
            agent.ui.click_yn(
                "account_no_matches",
                False,
                f"Account no matches IUW: {data.get('bank_account', 'N/A')}",
            )
            agent.state.log(
                "⚠️ Bank statement account number mismatch detected", "warning"
            )
        else:
            agent.ui.click_yn(
                "account_no_matches",
                True,
                f"Account no matches IUW: {data.get('bank_account', 'N/A')}",
            )

        if "name_mismatch" in issues:
            agent.ui.click_yn(
                "name_on_statement_matches",
                False,
                f"Name on statement matches: {data.get('name', 'N/A')}",
            )
            agent.state.log("⚠️ Bank statement name mismatch detected", "warning")
        else:
            agent.ui.click_yn(
                "name_on_statement_matches",
                True,
                f"Name on statement matches: {data.get('name', 'N/A')}",
            )

    # Extract bank details from validation results if available
    extracted_account = bank_details.get("extracted_data", {}).get(
        "account_number", data.get("bank_account", "")
    )
    extracted_ifsc = bank_details.get("extracted_data", {}).get(
        "ifsc_code", data.get("ifsc", "")
    )

    agent.ui.fill_text(
        "input_account_number_entered", extracted_account, "Account Number"
    )
    agent.ui.fill_text("input_ifsc_entered", extracted_ifsc, "IFSC Code")

    screenshot = agent.ui.screenshot()
    agent.state.add_screenshot("Card 2 - KYC Complete", screenshot)
    agent.state.log("✅ Bank Validation section filled", "success")


def fill_occupation(agent, data: dict):
    """Fill occupation & industry section via Playwright."""
    agent.state.set_step("Filling Occupation Section", "Card 3: Financial")
    agent.state.set_progress(0.82)
    agent.state.log("💼 Filling Occupation & Industry section...", "info")

    occupation = data.get("occupation", "Salaried")
    industry = data.get("industry", "IT/Software")

    # Map DB values to dropdown labels
    OCC_MAP = {
        "Salaried": "Salaried",
        "Self Employed": "Self Employed",
        "Business": "Business",
        "Professional": "Professional",
        "Retired": "Retired",
        "Homemaker": "Homemaker",
    }
    IND_MAP = {
        "IT/Software": "IT/Software",
        "Banking/Finance": "Banking/Finance",
        "Healthcare": "Healthcare",
        "Manufacturing": "Manufacturing",
        "Agriculture": "Agriculture",
        "Retail": "Retail",
        "Government": "Government",
    }
    HAZARDOUS_INDUSTRIES = {"Mining", "Oil & Gas", "Explosives", "Defence", "Fishing"}
    is_hazardous = industry in HAZARDOUS_INDUSTRIES

    agent.ui.scroll_to("sec-occ")
    agent.ui.select(
        "input_occupation", OCC_MAP.get(occupation, occupation), "Occupation"
    )
    agent.ui.select("input_industry_type", IND_MAP.get(industry, industry), "Industry")
    agent.ui.click_yn(
        "is_hazardous",
        is_hazardous,
        f"{'Hazardous' if is_hazardous else 'NOT hazardous'}: {industry}",
    )

    screenshot = agent.ui.screenshot()
    agent.state.add_screenshot("Card 3 - Occupation & Industry", screenshot)
    agent.state.log("✅ Occupation & Industry section filled", "success")


def fill_education(agent, data: dict):
    """Fill education validation section via Playwright."""
    agent.state.set_step("Filling Education Section", "Card 3: Financial")
    agent.state.set_progress(0.90)
    agent.state.log("🎓 Filling Education Validation section...", "info")

    edu_map = {
        "Graduate": "Graduate",
        "GRAD": "Graduate",
        "Post Graduate": "Post Graduate",
        "PG": "Post Graduate",
        "HSC / 12th": "HSC / 12th",
        "HSC": "HSC / 12th",
        "SSC / 10th": "SSC / 10th",
        "SSC": "SSC / 10th",
        "Other": "Other",
    }
    edu_value = edu_map.get(data.get("education", "Graduate"), "Graduate")

    agent.ui.scroll_to("sec-edu")
    agent.ui.select("input_education_level", edu_value, "Education Level")

    agent.state.log("✅ Education Validation section filled", "success")


def fill_nominee(agent, data: dict):
    """Fill nominee validation section via Playwright."""
    agent.state.set_step("Filling Nominee Section", "Card 3: Financial")
    agent.state.set_progress(0.96)
    agent.state.log("👨‍👩‍👧 Filling Nominee Validation section...", "info")

    agent.ui.scroll_to("sec-nominee")
    agent.ui.click_yn(
        "nominee_details_added",
        True,
        f"Nominee details added: {data.get('nominee_name', 'N/A')} ({data.get('nominee_relation', 'N/A')})",
    )

    agent.ui.wait(0.5)
    final_screenshot = agent.ui.screenshot()
    agent.state.add_screenshot("Final - Checklist Complete", final_screenshot)

    agent.ui.wait(0.3)
    agent.state.log("✅ Nominee Validation section filled", "success")
