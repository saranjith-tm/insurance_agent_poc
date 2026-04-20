import threading
from datetime import datetime

# Import VLM clients
from .vlm_clients.openrouter_client import OpenRouterClient


def get_vlm_client(model_config: dict, api_key: str):
    """Factory function to create the appropriate VLM client."""
    provider = model_config.get("provider", "openrouter")
    model_id = model_config.get("model_id")

    if provider == "openrouter":
        return OpenRouterClient(model_id=model_id, api_key=api_key)
    elif provider == "anthropic":
        from .vlm_clients.anthropic_client import AnthropicClient

        return AnthropicClient(model_id=model_id, api_key=api_key)
    elif provider == "openai":
        from .vlm_clients.openai_client import OpenAIVLMClient

        return OpenAIVLMClient(model_id=model_id, api_key=api_key)
    elif provider == "google":
        from .vlm_clients.google_client import GoogleVLMClient

        return GoogleVLMClient(model_id=model_id, api_key=api_key)
    else:
        raise ValueError(f"Unknown provider: {provider}")


class AutomationState:
    """Shared state for communicating between agent thread and UI."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.running = False
        self.completed = False
        self.error = None
        self.current_step = ""
        self.current_section = ""
        self.progress = 0.0  # 0.0 to 1.0
        self.log_entries = []
        self.screenshots = []  # List of (label, base64_png) tuples
        self.actions_taken = []  # List of action dicts
        self.extracted_data = {}  # Data extracted from sales agent app
        self.checklist_state = {}  # Current state of underwriting checklist
        self.latest_screenshot_b64 = None  # Most recent screenshot for live view
        self.video_path = None  # Path to recorded video file (WebM) after run
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_cost = 0.0
        self.image_confidence = 0.0  # Overall image quality/extraction confidence
        self.doc_confidences = {} # Individual doc confidence scores
        self.start_time = None
        self.end_time = None
        self._lock = threading.Lock()

    def log(self, message: str, level: str = "info", action: dict = None):
        with self._lock:
            entry = {
                "timestamp": datetime.now().strftime("%H:%M:%S"),
                "level": level,
                "message": message,
                "action": action,
            }
            self.log_entries.append(entry)
            if action:
                self.actions_taken.append(action)

    def add_screenshot(self, label: str, screenshot_bytes: bytes):
        """Store a screenshot for display in the dashboard."""
        with self._lock:
            import base64

            b64 = base64.b64encode(screenshot_bytes).decode()
            self.screenshots.append((label, b64))
            self.latest_screenshot_b64 = b64  # always keep the freshest frame
            # Keep only last 20 screenshots
            if len(self.screenshots) > 20:
                self.screenshots = self.screenshots[-20:]

    def set_step(self, step: str, section: str = ""):
        with self._lock:
            self.current_step = step
            if section:
                self.current_section = section

    def set_progress(self, value: float):
        with self._lock:
            self.progress = min(1.0, max(0.0, value))

    def update_usage(self, input_tokens: int, output_tokens: int, model_id: str):
        """Update cumulative token usage and cost."""
        from config import MODEL_PRICING

        with self._lock:
            self.input_tokens += input_tokens
            self.output_tokens += output_tokens

            # Calculate cost
            pricing = MODEL_PRICING.get(model_id, {"input": 0, "output": 0})
            step_cost = (input_tokens / 1_000_000 * pricing["input"]) + (
                output_tokens / 1_000_000 * pricing["output"]
            )
            self.total_cost += step_cost
