import time
import io
import httpx
from PIL import Image
from .vlm_clients.base import VLMAction


class PlaywrightHelper:
    """Helper class to encapsulate Playwright interactions and REST API operations."""

    def __init__(
        self, page, state, underwriting_url: str, application_no: str, step_delay: float
    ):
        self.page = page
        self.state = state
        self.underwriting_url = underwriting_url
        self.application_no = application_no
        self.step_delay = step_delay

    def screenshot(self) -> bytes:
        """Take a screenshot of the current page and update live-view state."""
        png = self.page.screenshot(type="png")
        import base64

        with self.state._lock:
            self.state.latest_screenshot_b64 = base64.b64encode(png).decode()
        return png

    def screenshot_as_pil(self) -> Image.Image:
        """Take a screenshot and return as PIL Image."""
        png_bytes = self.screenshot()
        return Image.open(io.BytesIO(png_bytes))

    def get_page_size(self):
        """Get current page dimensions."""
        size = self.page.viewport_size
        return size["width"], size["height"]

    def wait(self, seconds: float = None):
        """Wait for specified seconds (defaults to step_delay)."""
        time.sleep(seconds or self.step_delay)

    def execute_action(self, action: VLMAction):
        """Execute a VLM-suggested action in the browser."""
        if action.action == "click" and action.x and action.y:
            self.page.mouse.click(action.x, action.y)
            self.wait(0.5)

        elif action.action == "type" and action.x and action.y:
            # Click first, then type
            self.page.mouse.click(action.x, action.y)
            self.wait(0.3)
            if action.text:
                # Clear existing value first
                self.page.keyboard.press("Control+A")
                self.page.keyboard.type(action.text)
            self.wait(0.3)

        elif action.action == "select" and action.x and action.y:
            # For select dropdowns, click and then select by value
            self.page.mouse.click(action.x, action.y)
            self.wait(0.3)

        elif action.action == "scroll_down":
            self.page.mouse.wheel(0, 400)
            self.wait(0.5)

    def log_action(self, action: VLMAction):
        """Log a VLM action."""
        action_dict = action.to_dict()
        msg = f"  → {action.action.upper()}"
        if action.x and action.y:
            msg += f" at ({action.x}, {action.y})"
        if action.text:
            msg += f" text='{action.text}'"
        msg += f" | {action.element_description}"
        self.state.log(msg, "action", action_dict)

    def use_api_to_fill(self, field_id: str, value, is_click: bool = False) -> bool:
        """Use the underwriting app's REST API to fill a field directly (fast path)."""
        try:
            endpoint = "/api/click" if is_click else "/api/fill"
            payload = {
                "element_id": field_id,
                "value": value,
                "app_no": self.application_no,
            }
            resp = httpx.post(
                f"{self.underwriting_url}{endpoint}", json=payload, timeout=10
            )
            return resp.status_code == 200
        except Exception as e:
            self.state.log(f"  API fill error for {field_id}: {e}", "warning")
            return False

    def api_click(self, field_id: str, value: bool, label: str):
        """Click a yes/no field via REST API and log it."""
        ok = self.use_api_to_fill(field_id, value, is_click=True)
        icon = "✅" if value else "❌"
        self.state.log(f"  {icon} {'YES' if value else 'NO'}: {label}", "action")
        return ok

    def api_fill(self, field_id: str, value: str, label: str):
        """Fill a text/select field via REST API and log it."""
        ok = self.use_api_to_fill(field_id, value, is_click=False)
        self.state.log(f"  ✏️  {label} = '{value}'", "action")
        return ok

    # ------------------------------------------------------------------
    # Playwright-based helpers (visually click/fill in the browser)
    # ------------------------------------------------------------------

    def click_yn(self, field_id: str, is_yes: bool, label: str):
        """Click a Yes or No button via Playwright so it's visible in browser."""
        suffix = "yes" if is_yes else "no"
        btn_id = f"btn_{field_id}_{suffix}"
        # Auto-scroll to centering first
        self.scroll_to(f"sec-{field_id.split('_')[0]}") # Try to scroll to section
        self._use_playwright_to_click_yn(btn_id)
        
        # Update live view
        self.screenshot()
        
        icon = "✅" if is_yes else "❌"
        self.state.log(
            f"  {icon} Clicked {'YES' if is_yes else 'NO'}: {label}", "action"
        )

    def fill_text(self, input_id: str, value: str, label: str):
        """Type into a text field via Playwright."""
        # Auto-scroll to centering first
        target_id = input_id.replace('input_', '') if input_id.startswith('input_') else input_id
        self.scroll_to(target_id)
        self._use_playwright_to_fill_text(input_id, value)
        
        # Update live view
        self.screenshot()
        
        self.state.log(f"  ✏️  {label} = '{value}'", "action")

    def select(self, input_id: str, value: str, label: str):
        """Choose a dropdown option via Playwright."""
        # Auto-scroll to centering first
        self.scroll_to(input_id)
        self._use_playwright_to_fill_select(f"#{input_id}", value)
        
        # Update live view
        self.screenshot()
        
        self.state.log(f"  📋 {label} = '{value}'", "action")

    def scroll_to(self, element_id: str):
        """Scroll the section into view so the user can see it being filled."""
        try:
            self.page.evaluate(
                f"document.getElementById('{element_id}') && "
                f"document.getElementById('{element_id}').scrollIntoView({{behavior:'smooth',block:'center'}})"
            )
            self.wait(0.3)
        except Exception:
            pass

    def _use_playwright_to_fill_select(self, selector: str, value: str):
        """Select a dropdown option and trigger onchange so the API call fires."""
        try:
            self.page.select_option(selector, label=value)
        except Exception:
            try:
                self.page.select_option(selector, value=value)
            except Exception as e:
                self.state.log(
                    f"  Could not select '{value}' in {selector}: {e}", "warning"
                )
                return
        # Trigger the onchange handler (calls fillField → /api/fill)
        self.page.dispatch_event(selector, "change")
        self.wait(0.15)

    def _use_playwright_to_click_yn(self, btn_id: str):
        """Click a Yes/No button by its HTML ID."""
        try:
            selector = f"#{btn_id}"
            self.page.wait_for_selector(selector, timeout=5000)
            self.page.click(selector)
            self.wait(0.3)
        except Exception as e:
            self.state.log(f"  Could not click #{btn_id}: {e}", "warning")

    def _use_playwright_to_fill_text(self, input_id: str, value: str):
        """Fill a text input by its HTML ID and trigger the onchange handler."""
        try:
            selector = f"#{input_id}"
            self.page.wait_for_selector(selector, timeout=5000)
            self.page.fill(selector, str(value))
            self.page.dispatch_event(selector, "change")
            self.wait(0.2)
        except Exception as e:
            self.state.log(f"  Could not fill #{input_id}: {e}", "warning")

    def find_and_click_document(self, selector: str, doc_type: str) -> bool:
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
                element = self.page.query_selector(sel)
                if element:
                    element.click()
                    self.wait(0.5)
                    return True
            except Exception:
                continue

        return False
