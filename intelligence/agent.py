"""
Core Underwriting Automation Agent.

This agent automates the manual underwriting process:
1. Opens the Sales Agent app and extracts applicant data using VLM
2. Opens the Underwriting Checklist app
3. Uses VLM to analyze each section and fill in the appropriate responses
4. Runs a computer-use style loop: screenshot → VLM analysis → action → repeat

The agent communicates its progress via a shared state dict (for Streamlit integration).
"""

import threading
from .tools import navigation, extraction, verification, checklist, submit, bank_statement
import traceback
from datetime import datetime


# Import VLM clients
from .helpers import AutomationState, get_vlm_client
from .playwright_helper import PlaywrightHelper


class UnderwritingAgent:
    """
    Main automation agent that uses Playwright + VLM to automate the underwriting checklist.

    Architecture:
    - Uses Playwright to control a headless/headed browser
    - Takes screenshots of the underwriting app at each step
    - Sends screenshots + context to VLM for analysis
    - Executes the actions suggested by VLM (click, type, select)
    - Validates each action and retries if needed
    """

    AUTOMATION_STEPS = [
        # (step_name, section, task_description, progress)
        (
            "navigate_to_sales_agent",
            "Sales Agent App",
            "Navigate to sales agent application using application number",
            0.02,
        ),
        (
            "extract_single_screen_data",
            "Sales Agent App - Single Screen",
            "Extract applicant details from the single screen view",
            0.08,
        ),
        (
            "initial_checklist_fill",
            "Underwriting App",
            "Fill initial underwriter checklist with extracted data",
            0.25,
        ),
        (
            "navigate_to_documents",
            "Sales Agent App - Documents",
            "Navigate to view all documents screen",
            0.35,
        ),
        (
            "verify_documents",
            "Document Verification",
            "Verify uploaded documents quality and content",
            0.55,
        ),
        (
            "extract_min_balance",
            "Document Analysis",
            "Find minimum balance from bank statement documents",
            0.75,
        ),
        (
            "final_checklist_update",
            "Underwriting App - Final",
            "Update checklist with document verification results",
            0.85,
        ),
        ("complete", "Completed", "Enhanced underwriting automation completed", 1.0),
    ]

    def __init__(
        self,
        vlm_client,
        sales_agent_url: str,
        underwriting_url: str,
        state: AutomationState,
        application_no: str = "OS121345678",
        step_delay: float = 2.0,
        use_visual_mode: bool = True,
        headed: bool = False,
        record_video: bool = False,
        video_dir: str = "recordings",
    ):
        self.vlm = vlm_client
        self.sales_url = sales_agent_url
        self.underwriting_url = underwriting_url
        self.state = state
        self.application_no = application_no
        self.step_delay = step_delay
        self.use_visual_mode = (
            use_visual_mode  # If True, use VLM. If False, use API directly.
        )
        self.headed = headed
        self.record_video = record_video
        self.video_dir = video_dir
        self.browser = None
        self.page = None
        self.ui = None
        self._applicant_data = {}

    def run(self):
        """Main entry point - runs the full automation loop."""
        self.state.start_time = datetime.now()
        self.state.running = True
        self.state.log("🚀 Starting underwriting automation agent", "info")

        try:
            import os
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                # Launch browser
                launch_args = ["--no-sandbox", "--disable-dev-shm-usage"]
                self.state.log(
                    f"🌐 Launching browser (headed={self.headed}, record_video={self.record_video})...",
                    "info",
                )
                try:
                    self.browser = p.chromium.launch(
                        headless=not self.headed,
                        args=launch_args,
                    )
                except Exception as launch_err:
                    if self.headed:
                        self.state.log(
                            "⚠️ Headed mode failed (no display?), falling back to headless",
                            "warning",
                        )
                        self.browser = p.chromium.launch(
                            headless=True,
                            args=launch_args,
                        )
                    else:
                        raise launch_err

                # Context options
                context_kwargs = {"viewport": {"width": 1280, "height": 900}}
                if self.record_video:
                    os.makedirs(self.video_dir, exist_ok=True)
                    context_kwargs["record_video_dir"] = self.video_dir
                    context_kwargs["record_video_size"] = {"width": 1280, "height": 900}
                    self.state.log(
                        f"🎬 Video recording enabled → {self.video_dir}/", "info"
                    )

                context = self.browser.new_context(**context_kwargs)
                self.page = context.new_page()
                self.ui = PlaywrightHelper(
                    page=self.page,
                    state=self.state,
                    underwriting_url=self.underwriting_url,
                    application_no=self.application_no,
                    step_delay=self.step_delay,
                )
                self.state.log("✅ Browser launched (1280x900)", "success")

                # Run enhanced automation steps
                navigation.run_step_navigate_to_sales_agent(self)
                if not self.state.running:
                    return

                extraction.run_step_extract_single_screen_data(self)
                if not self.state.running:
                    return

                navigation.run_step_navigate_to_documents(self)
                if not self.state.running:
                    return

                verification.run_step_verify_documents(self)
                if not self.state.running:
                    return

                bank_statement.run_step_extract_min_balance(self)
                if not self.state.running:
                    return

                checklist.run_step_final_checklist_update(self)
                if not self.state.running:
                    return

                submit.run_step_submit(self)

                self.state.set_step("Complete", "Completed")
                self.state.set_progress(1.0)
                self.state.log(
                    "🎉 Underwriting checklist automation COMPLETED successfully!",
                    "success",
                )
                self.state.completed = True

        except Exception as e:
            error_msg = f"❌ Automation error: {str(e)}\n{traceback.format_exc()}"
            self.state.log(error_msg, "error")
            self.state.error = str(e)
        finally:
            # Save video path before closing context (Playwright finalises file on context.close())
            _video_path = None
            if self.record_video and self.page:
                try:
                    _video_path = self.page.video.path()
                except Exception:
                    pass

            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass

            if _video_path:
                self.state.video_path = _video_path
                self.state.log(f"🎬 Video saved → {_video_path}", "success")

            self.state.running = False
            self.state.end_time = datetime.now()


def run_automation_in_thread(
    model_config: dict,
    api_key: str,
    sales_agent_url: str,
    underwriting_url: str,
    application_no: str,
    state: AutomationState,
    use_visual_mode: bool = True,
    step_delay: float = 1.5,
    headed: bool = False,
    record_video: bool = False,
    video_dir: str = "recordings",
) -> threading.Thread:
    """
    Start the automation agent in a background thread.
    Returns the thread object.
    """
    state.reset()

    def _run():
        try:
            vlm_client = get_vlm_client(model_config, api_key)
            agent = UnderwritingAgent(
                vlm_client=vlm_client,
                sales_agent_url=sales_agent_url,
                underwriting_url=underwriting_url,
                state=state,
                application_no=application_no,
                step_delay=step_delay,
                use_visual_mode=use_visual_mode,
                headed=headed,
                record_video=record_video,
                video_dir=video_dir,
            )
            agent.run()
        except Exception as e:
            state.log(f"❌ Fatal error: {str(e)}\n{traceback.format_exc()}", "error")
            state.error = str(e)
            state.running = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread
