def run_step_navigate_to_sales_agent(agent):
    """Step 1: Navigate to sales agent application using application number."""
    agent.state.set_step("Navigating to Sales Agent", "Sales Agent App")
    agent.state.set_progress(0.02)
    agent.state.log(
        f"Opening sales agent app for application {agent.application_no}...", "info"
    )

    try:
        # Navigate to the sales agent queue first
        agent.page.goto(f"{agent.sales_url}/")
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        agent.ui.wait(1.0)

        # Take screenshot of queue
        screenshot = agent.ui.screenshot()
        agent.state.add_screenshot("Sales Agent - Queue View", screenshot)

        # Navigate to the specific application
        agent.page.goto(f"{agent.sales_url}/case/{agent.application_no}")
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        agent.ui.wait(1.0)

        # Take screenshot of application page
        screenshot = agent.ui.screenshot()
        agent.state.add_screenshot("Sales Agent - Application Opened", screenshot)

        agent.state.log(
            f"Successfully opened sales agent app for {agent.application_no}", "success"
        )

    except Exception as e:
        agent.state.log(f"Failed to navigate to sales agent: {e}", "error")
        raise


def run_step_navigate_to_documents(agent):
    """Step 4: Navigate to view all documents screen."""
    agent.state.set_step("Navigating to Documents", "Sales Agent App - Documents")
    agent.state.set_progress(0.35)
    agent.state.log("Navigating to view all documents screen...", "info")

    try:
        # Navigate back to sales agent documents
        agent.page.goto(f"{agent.sales_url}/case/{agent.application_no}/docs")
        agent.page.wait_for_load_state("domcontentloaded", timeout=15000)
        agent.ui.wait(1.0)

        # Take screenshot of documents page
        screenshot = agent.ui.screenshot()
        agent.state.add_screenshot("Sales Agent - All Documents View", screenshot)

        agent.state.log("Successfully opened view all documents screen", "success")

    except Exception as e:
        agent.state.log(f"Failed to navigate to documents: {e}", "error")
        raise
