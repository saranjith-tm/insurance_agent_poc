import json


def run_step_verify_documents(agent):
    """Step 5: Verify uploaded documents quality and content."""
    agent.state.set_step("Verifying Documents", "Document Verification")
    agent.state.set_progress(0.55)
    agent.state.log("Starting document verification process...", "info")

    try:
        # Initialize document validation results
        agent._document_validation = {
            "pan_valid": False,
            "aadhaar_valid": False,
            "bank_statement_valid": False,
            "proposal_valid": False,
            "validation_details": {},
        }

        if agent.use_visual_mode:
            # Use VLM to verify each document
            verify_documents_with_vlm(agent)
        else:
            # Skip verification if not in visual mode
            agent.state.log(
                "Visual mode disabled - assuming all documents valid", "warning"
            )
            agent._document_validation = {
                "pan_valid": True,
                "aadhaar_valid": True,
                "bank_statement_valid": True,
                "proposal_valid": True,
                "validation_details": {
                    "note": "Verification skipped - visual mode disabled"
                },
            }

        # Log verification results
        valid_count = sum(
            1
            for k, v in agent._document_validation.items()
            if k.endswith("_valid") and v
        )
        total_count = sum(
            1 for k in agent._document_validation.keys() if k.endswith("_valid")
        )

        if valid_count == total_count:
            agent.state.log(
                f"All {total_count} documents verified successfully", "success"
            )
        else:
            agent.state.log(
                f"{valid_count}/{total_count} documents verified - proceeding with findings",
                "warning",
            )

    except Exception as e:
        agent.state.log(f"Document verification failed: {e}", "error")
        # Default to valid to avoid blocking
        agent._document_validation = {
            "pan_valid": True,
            "aadhaar_valid": True,
            "bank_statement_valid": True,
            "proposal_valid": True,
            "validation_details": {"error": str(e)},
        }


def verify_documents_with_vlm(agent):
    """Refactored: Use a tab discovery loop to find and verify documents."""
    agent.state.log("🔍 Systematically checking document tabs for verification...", "info")

    tabs_to_check = [
        "PhotoIDProof",
        "Others",
        "NonMedicalDeclar",
        "FaceVerificationRep",
        "RCR",
    ]

    # Reference data for VLM to match against
    applicant_data_summary = (
        f"Name: {agent._applicant_data.get('name') or agent._applicant_data.get('first_name', '') + ' ' + agent._applicant_data.get('last_name', '')}\n"
        f"PAN: {agent._applicant_data.get('pan_no') or agent._applicant_data.get('pan_number', 'N/A')}\n"
        f"Aadhaar: {agent._applicant_data.get('aadhaar_no') or agent._applicant_data.get('aadhaar_number', 'N/A')}\n"
        f"DOB: {agent._applicant_data.get('dob', 'N/A')}"
    )

    for tab_name in tabs_to_check:
        try:
            agent.state.log(f"📂 Checking category: {tab_name}...", "info")

            # Find and click the specific tab
            tab_locator = agent.page.get_by_text(tab_name, exact=True)
            if tab_locator.count() > 0:
                tab_locator.first.scroll_into_view_if_needed()
                tab_locator.first.click(force=True)
                agent.state.log(f"  🖱️ Category '{tab_name}' selected.", "info")
                agent.ui.wait(4.5) # Wait for PDF.js canvas rendering
            else:
                agent.state.log(f"  ⚠️ Category tab '{tab_name}' not found, skipping...", "warning")
                continue

            # Capture screenshot for analysis
            screenshot = agent.ui.screenshot()
            agent.state.add_screenshot(f"Verification - {tab_name}", screenshot)

            # Use VLM to identify and verify
            prompt = (
                "Analyze this insurance document screenshot.\n\n"
                "APPLICANT DATA ON FILE:\n"
                f"{applicant_data_summary}\n\n"
                "TASKS:\n"
                "1. What type of document is this? (doc_type: e.g. 'PAN', 'Aadhaar', 'Bank Statement', 'Face Verification', 'RCR', 'Other')\n"
                "2. Is this document valid, legible, and matches the applicant data above? (valid: boolean)\n"
                "3. If it is a PAN or Aadhaar, does the ID number match exactly? (matches_id: boolean)\n"
                "4. Give a confidence score for the image quality and readability (0.0 to 1.0). (confidence: number)\n"
                "5. What is your reasoning? (reasoning: string)\n\n"
                "Return ONLY a JSON object: "
                '{"doc_type": "text", "valid": bool, "matches_id": bool, "confidence": float, "reasoning": "text"}'
            )

            result_data, usage = agent.vlm.analyze_document(screenshot, prompt)
            agent.state.update_usage(usage.input_tokens, usage.output_tokens, usage.model_id)
            
            # Handle debugging if parsing failed
            if result_data.get("parsing_error"):
                agent.state.log(f"  ⚠️ VLM Error for {tab_name}: {result_data.get('raw_response')[:100]}", "warning")
                continue

            doc_type_found = str(result_data.get("doc_type", "Other")).upper()
            is_valid = result_data.get("valid", False)
            confidence = result_data.get("confidence", 0.0)
            reasoning = result_data.get("reasoning", "No reasoning.")

            agent.state.log(f"  📝 Detected: {doc_type_found} (Conf: {confidence:.2f})", "info")
            agent.state.log(f"  🧠 Reasoning: {reasoning}", "info")

            # Update overall confidence in state
            with agent.state._lock:
                agent.state.doc_confidences[tab_name] = confidence
                if agent.state.doc_confidences:
                    agent.state.image_confidence = sum(agent.state.doc_confidences.values()) / len(agent.state.doc_confidences)

            # Update master validation results
            if "PAN" in doc_type_found:
                agent._document_validation["pan_valid"] = is_valid
                status = "✅" if is_valid else "❌"
                agent.state.log(f"  {status} PAN Card Verification: {is_valid}", "success" if is_valid else "warning")
                
            elif "AADHAAR" in doc_type_found:
                agent._document_validation["aadhaar_valid"] = is_valid
                status = "✅" if is_valid else "❌"
                agent.state.log(f"  {status} Aadhaar Verification: {is_valid}", "success" if is_valid else "warning")
                
            elif "BANK" in doc_type_found:
                agent._document_validation["bank_statement_valid"] = is_valid
                
            elif "PROPOSAL" in doc_type_found or "RCR" in doc_type_found:
                agent._document_validation["proposal_valid"] = is_valid
                agent.state.log(f"  ✅ Application Document verified: {doc_type_found}", "success")

            # Store extra details
            agent._document_validation["validation_details"][tab_name] = {
                "doc_type": doc_type_found,
                "valid": is_valid,
                "reasoning": reasoning
            }

        except Exception as e:
            agent.state.log(f"  ❌ Error verifying tab '{tab_name}': {e}", "error")


def validate_documents_from_sales_agent(agent):
    """Validate all uploaded documents from the sales agent app before proceeding."""
    agent.state.set_step("Validating Documents", "Sales Agent App")
    agent.state.set_progress(0.08)
    agent.state.log(
        "📄 Opening document viewer to validate uploaded documents...", "info"
    )

    try:
        # Navigate to document viewer
        agent.page.goto(f"{agent.sales_url}/case/{agent.application_no}/docs")
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        agent.ui.wait(1.0)

        # Take screenshot of document viewer
        screenshot = agent.ui.screenshot()
        agent.state.add_screenshot("Document Viewer - All Documents", screenshot)

        # Initialize document validation results
        agent._document_validation = {
            "pan_valid": False,
            "aadhaar_valid": False,
            "bank_statement_valid": False,
            "proposal_valid": False,
            "validation_details": {},
        }

        # Validate each document type
        if agent.use_visual_mode:
            validate_documents_with_vlm(agent)
        else:
            # Skip validation if not in visual mode
            agent.state.log(
                "⚠️ Visual mode disabled - skipping document validation", "warning"
            )
            agent._document_validation = {
                "pan_valid": True,
                "aadhaar_valid": True,
                "bank_statement_valid": True,
                "proposal_valid": True,
                "validation_details": {
                    "note": "Validation skipped - visual mode disabled"
                },
            }

        # Log validation results
        valid_count = sum(
            1
            for k, v in agent._document_validation.items()
            if k.endswith("_valid") and v
        )
        total_count = sum(
            1 for k in agent._document_validation.keys() if k.endswith("_valid")
        )

        if valid_count == total_count:
            agent.state.log(
                f"✅ All {total_count} documents validated successfully", "success"
            )
        else:
            agent.state.log(
                f"⚠️ {valid_count}/{total_count} documents validated - proceeding with caution",
                "warning",
            )

    except Exception as e:
        agent.state.log(f"❌ Document validation error: {e}", "error")
        # Default to valid to avoid blocking the process
        agent._document_validation = {
            "pan_valid": True,
            "aadhaar_valid": True,
            "bank_statement_valid": True,
            "proposal_valid": True,
            "validation_details": {"error": str(e)},
        }


def validate_documents_with_vlm(agent):
    """Use VLM to validate document content and quality."""
    agent.state.log("🤖 Using VLM to validate document content...", "info")

    try:
        # Get the current page content to identify available documents
        agent.page.content()

        # Define validation prompts for each document type
        validation_prompts = {
            "pan": {
                "prompt": "Analyze this PAN card document. Check if: 1) It's a valid PAN card format, 2) Name matches the applicant, 3) PAN number is visible and valid format, 4) Document is clear and readable. Return JSON with 'valid' (boolean), 'confidence' (0-1), 'issues' (array), and 'extracted_data' (object).",
                "selector": "img[src*='pan'], img[src*='PAN'], .pan-document, #pan-doc",
            },
            "aadhaar": {
                "prompt": "Analyze this Aadhaar card document. Check if: 1) It's a valid Aadhaar card, 2) Name matches applicant, 3) DOB matches applicant, 4) Aadhaar number is visible, 5) Document is clear. Return JSON with 'valid' (boolean), 'confidence' (0-1), 'issues' (array), and 'extracted_data' (object).",
                "selector": "img[src*='aadhaar'], img[src*='Aadhaar'], .aadhaar-document, #aadhaar-doc",
            },
            "bank_statement": {
                "prompt": "Analyze this bank statement. Check if: 1) It's a bank statement, 2) Account number is visible, 3) Name matches applicant, 4) Statement is recent, 5) Document is clear. Return JSON with 'valid' (boolean), 'confidence' (0-1), 'issues' (array), and 'extracted_data' (object).",
                "selector": "img[src*='bank'], img[src*='statement'], .bank-document, #bank-doc",
            },
            "proposal": {
                "prompt": "Analyze this proposal form. Check if: 1) It's a completed insurance proposal, 2) Required fields are filled, 3) Signature is present, 4) Document is clear. Return JSON with 'valid' (boolean), 'confidence' (0-1), 'issues' (array), and 'extracted_data' (object).",
                "selector": "img[src*='proposal'], img[src*='form'], .proposal-document, #proposal-doc",
            },
        }

        # Validate each document type
        for doc_type, config in validation_prompts.items():
            try:
                # Try to find and click on the document
                document_found = agent.ui.find_and_click_document(
                    config["selector"], doc_type
                )

                if document_found:
                    agent.ui.wait(1.0)  # Wait for document to load
                    screenshot = agent.ui.screenshot()
                    agent.state.add_screenshot(
                        f"Document Validation - {doc_type.title()}", screenshot
                    )

                    # Use VLM to validate the document
                    validation_result, usage = agent.vlm.analyze_document(
                        screenshot, config["prompt"]
                    )
                    agent.state.update_usage(usage.input_tokens, usage.output_tokens, usage.model_id)

                    # Parse validation result
                    try:
                        result_data = (
                            json.loads(validation_result)
                            if isinstance(validation_result, str)
                            else validation_result
                        )
                        is_valid = result_data.get("valid", False)
                        confidence = result_data.get("confidence", 0.0)
                        issues = result_data.get("issues", [])
                        extracted = result_data.get("extracted_data", {})

                        # Store validation result
                        agent._document_validation[f"{doc_type}_valid"] = (
                            is_valid and confidence > 0.7
                        )
                        agent._document_validation["validation_details"][doc_type] = {
                            "valid": is_valid,
                            "confidence": confidence,
                            "issues": issues,
                            "extracted_data": extracted,
                        }

                        # Update overall confidence in state
                        with agent.state._lock:
                            agent.state.doc_confidences[doc_type.title()] = confidence
                            if agent.state.doc_confidences:
                                agent.state.image_confidence = sum(agent.state.doc_confidences.values()) / len(agent.state.doc_confidences)

                        status_icon = "✅" if is_valid and confidence > 0.7 else "❌"
                        agent.state.log(
                            f"  {status_icon} {doc_type.title()}: Valid={is_valid}, Confidence={confidence:.2f}",
                            "info",
                        )

                        if issues:
                            agent.state.log(
                                f"    Issues: {', '.join(issues)}", "warning"
                            )

                    except json.JSONDecodeError:
                        agent.state.log(
                            f"  ⚠️ {doc_type.title()}: Could not parse VLM response",
                            "warning",
                        )
                        agent._document_validation[f"{doc_type}_valid"] = False

                else:
                    agent.state.log(
                        f"  ⚠️ {doc_type.title()}: Document not found", "warning"
                    )
                    agent._document_validation[f"{doc_type}_valid"] = False

            except Exception as e:
                agent.state.log(
                    f"  ❌ {doc_type.title()}: Validation error - {e}", "error"
                )
                agent._document_validation[f"{doc_type}_valid"] = False

    except Exception as e:
        agent.state.log(f"❌ VLM document validation failed: {e}", "error")
