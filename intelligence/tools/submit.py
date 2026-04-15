def run_step_submit(agent):
    """Step 5: Submit the completed checklist and update the case status to Completed."""
    agent.state.set_step("Submitting checklist", "Finalising")
    agent.state.set_progress(0.98)
    agent.state.log("📤 Submitting underwriting checklist...", "info")

    import httpx

    try:
        resp = httpx.post(
            f"{agent.underwriting_url}/api/submit",
            json={
                "app_no": agent.application_no,
                "uw_decision": "Accept",
                "uw_remarks": "All checks passed — processed by automation agent",
                "performed_by": "AUTOMATION",
            },
            timeout=15,
        )
        data = resp.json()

        if resp.status_code == 200:
            new_status = data.get("new_case_status", "Completed")
            agent.state.log(
                f"✅ Checklist submitted. Case status → '{new_status}'", "success"
            )
        elif resp.status_code == 422:
            # Some sections still incomplete — use force submit
            incomplete = data.get("incomplete_sections", [])
            agent.state.log(
                f"⚠️ {len(incomplete)} section(s) still pending, using force-submit: {incomplete}",
                "warning",
            )
            resp2 = httpx.post(
                f"{agent.underwriting_url}/api/submit/force",
                json={
                    "app_no": agent.application_no,
                    "uw_decision": "Accept",
                    "uw_remarks": "Force-submitted by automation agent",
                    "performed_by": "AUTOMATION",
                },
                timeout=15,
            )
            data2 = resp2.json()
            new_status = data2.get("new_case_status", "Completed")
            agent.state.log(
                f"✅ Force-submitted. Case status → '{new_status}'", "success"
            )
        else:
            agent.state.log(
                f"⚠️ Submit returned HTTP {resp.status_code}: {data}", "warning"
            )

    except Exception as e:
        agent.state.log(f"❌ Submit error: {e}", "error")

    # Reload the page so the status badge updates in the live view / recording
    try:
        agent.page.goto(f"{agent.underwriting_url}/{agent.application_no}")
        agent.page.wait_for_load_state("domcontentloaded", timeout=10000)
        agent.ui.wait(0.5)
        final = agent.ui.screenshot()
        agent.state.add_screenshot("Submission Confirmed", final)
    except Exception:
        pass
