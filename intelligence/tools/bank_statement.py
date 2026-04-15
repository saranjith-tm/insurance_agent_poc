import json


def run_step_extract_min_balance(agent):
    """Step 5.5: Find minimum balance from bank statement documents."""
    agent.state.set_step("Finding Minimum Balance", "Document Analysis")
    agent.state.set_progress(0.75)
    agent.state.log("🔍 Searching for bank statement to find minimum balance...", "info")

    # The user specified these categories to check
    tabs_to_check = [
        "PhotoIDProof",
        "Others",
        "NonMedicalDeclar",
        "FaceVerificationRep",
        "RCR",
    ]

    try:
        # Navigate to view all documents screen if not already there
        if "/docs" not in agent.page.url:
            agent.state.log("Navigating to view all documents screen...", "info")
            agent.page.goto(f"{agent.sales_url}/case/{agent.application_no}/docs")
            agent.page.wait_for_load_state("domcontentloaded", timeout=20000)
            agent.ui.wait(1.0)

        min_balance = None
        bank_stmt_tab = None

        for tab_name in tabs_to_check:
            try:
                agent.state.log(f"📂 Checking tab: {tab_name}...", "info")

                # Use the most robust locator to find the specific tab text
                tab_locator = agent.page.get_by_text(tab_name, exact=True)
                
                if tab_locator.count() > 0:
                    agent.state.log(f"  🖱️ Found tab '{tab_name}', clicking...", "info")
                    tab_locator.first.scroll_into_view_if_needed()
                    tab_locator.first.click(force=True)
                    agent.state.log(f"  ✅ Tab '{tab_name}' clicked successfully", "info")
                    agent.state.log("  ⏳ Waiting for document/PDF to render...", "info")
                    agent.ui.wait(4.5)  # Extended wait specifically for PDF rendering
                else:
                    agent.state.log(f"  ⚠️ Tab '{tab_name}' not found, skipping...", "warning")
                    continue

                # Now identify if it's a bank statement and scroll to find the overall min balance
                max_scrolls = 5
                current_scroll = 0
                is_actually_bank_stmt = False

                while current_scroll < max_scrolls:
                    page_num = current_scroll + 1
                    agent.state.log(f"  📸 Analyzing {tab_name} - Page {page_num}...", "info")
                    
                    # Take screenshot of the displayed document area
                    screenshot = agent.ui.screenshot()
                    agent.state.add_screenshot(f"Analysis - {tab_name} - Page {page_num}", screenshot)

                    # Use VLM to identify the document and extract values
                    prompt = (
                        "Analyze this document screenshot.\n"
                        f"Target: Extract minimum balance from {tab_name} (Page {page_num}).\n\n"
                        "1. What is the document title? (doc_title: string)\n"
                        "2. Is this a Bank Statement? (is_bank_statement: boolean)\n"
                        "3. Find the LOWEST value in the 'Balance' column. (minimum_balance: number or null)\n"
                        "4. Reasoning: (reasoning: string)\n\n"
                        "Return ONLY JSON: "
                        '{"doc_title": "text", "is_bank_statement": bool, "minimum_balance": val, "reasoning": "text"}'
                    )

                    result_data = agent.vlm.analyze_document(screenshot, prompt)
                    
                    # Handle debugging if parsing failed
                    if result_data.get("parsing_error"):
                        agent.state.log(f"  ⚠️ VLM JSON Parsing Error. Raw response: {result_data.get('raw_response')[:200]}...", "warning")
                        # If we can't parse, but it's a known bank statement tab, keep going
                        if tab_name in ["NonMedicalDeclar", "RCR"]:
                             is_bank = True
                             title = "Unknown (Trusted Tab)"
                             reasoning = "Parsing error but tab is trusted."
                        else:
                             break
                    else:
                        title = str(result_data.get("doc_title", "")).lower()
                        reasoning = result_data.get("reasoning", "No reasoning provided.")
                        is_bank = result_data.get("is_bank_statement", False)
                        agent.state.log(f"  📝 Detected Title: '{result_data.get('doc_title')}'", "info")

                    # STICKY LOGIC: Force identification for known tabs
                    if current_scroll == 0:
                        is_trusted_tab = tab_name in ["NonMedicalDeclar", "RCR"]
                        stmt_keywords = ["statement", "account", "bank", "balance", "transaction", "standard"]
                        matches_keywords = any(kw in title or kw in reasoning.lower() for kw in stmt_keywords)
                        
                        if is_bank or matches_keywords or is_trusted_tab:
                            agent.state.log(f"  🎯 Tab '{tab_name}' identified as Bank Statement. Proceeding...", "success")
                            is_actually_bank_stmt = True
                        else:
                            agent.state.log(f"  ℹ️ Tab '{tab_name}' does not appear to be a bank statement. Skipping...", "info")
                            break
                    
                    is_actually_bank_stmt = True
                    val = result_data.get("minimum_balance")
                    
                    if val is not None:
                        try:
                            # Try to normalize numeric value
                            if isinstance(val, str):
                                val_num = float(val.replace(",", "").replace("₹", "").strip())
                            else:
                                val_num = float(val)

                            if min_balance is None or val_num < float(str(min_balance).replace(",", "")):
                                min_balance = val_num
                                bank_stmt_tab = tab_name
                                agent.state.log(f"  ✨ Found lower balance on Page {page_num}: {val_num}", "success")
                        except (ValueError, TypeError):
                            agent.state.log(f"  ⚠️ Could not parse balance '{val}' on page {page_num}", "warning")

                    # Scroll down one viewport for the next page
                    agent.state.log(f"  🖱️ Scrolling down {tab_name}...", "info")
                    is_at_bottom = agent.page.evaluate("""() => {
                        const el = document.getElementById('docPanel');
                        if (!el) return true;
                        const prevTop = el.scrollTop;
                        el.scrollTop += (el.clientHeight * 0.8); 
                        return Math.abs(el.scrollTop - prevTop) < 5 || (el.scrollTop + el.clientHeight >= el.scrollHeight - 10);
                    }""")

                    if is_at_bottom:
                        agent.state.log(f"  🔚 Reached bottom of {tab_name}.", "info")
                        break
                    
                    current_scroll += 1
                    agent.ui.wait(1.5) # Wait for render after scroll

                if is_actually_bank_stmt and min_balance is not None:
                    agent.state.log(f"✅ Finished processing '{tab_name}'. Final Min Balance so far: {min_balance}", "success")
                    break # Stop looking at other tabs if we found it

            except Exception as tab_err:
                agent.state.log(f"  ❌ Error processing tab {tab_name}: {tab_err}", "error")

        if min_balance is not None:
            # Store it in applicant data for later use in checklist filling
            agent._applicant_data["minimum_balance"] = str(min_balance)
            agent.state.log(
                f"✨ Successfully identified overall minimum balance: {min_balance}", "success"
            )
        else:
            agent.state.log(
                "⚠️ No bank statement with minimum balance found in the specified tabs.",
                "warning",
            )
            agent._applicant_data["minimum_balance"] = "Not Found"

    except Exception as e:
        agent.state.log(f"❌ Error during minimum balance extraction: {e}", "error")
        agent._applicant_data["minimum_balance"] = "Error"
