"""
Google Gemini VLM Client - supports Gemini 1.5 Pro and Gemini Vision models.
"""

import json
from .base import (
    BaseVLMClient,
    VLMAction,
    SYSTEM_PROMPT,
    ACTION_PROMPT_TEMPLATE,
    EXTRACTION_PROMPT_TEMPLATE,
)


class GoogleVLMClient(BaseVLMClient):
    """Client for Google Gemini Vision API."""

    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            self.genai = genai
            self.model = genai.GenerativeModel(
                model_name=model_id, system_instruction=SYSTEM_PROMPT
            )
        except ImportError:
            raise ImportError(
                "google-generativeai not installed. Run: pip install google-generativeai"
            )

    def _call_api(self, parts: list, max_tokens: int = 1024) -> str:
        """Make API call to Google Gemini."""
        generation_config = self.genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.1,
        )
        response = self.model.generate_content(
            parts, generation_config=generation_config
        )
        return response.text

    def analyze_and_act(
        self,
        screenshot_bytes: bytes,
        task_description: str,
        context: dict,
        image_width: int,
        image_height: int,
    ) -> VLMAction:
        """Analyze screenshot and determine next action."""
        prompt = ACTION_PROMPT_TEMPLATE.format(
            applicant_data=json.dumps(context.get("applicant_data", {}), indent=2),
            task_description=task_description,
            width=image_width,
            height=image_height,
        )

        parts = [{"mime_type": "image/png", "data": screenshot_bytes}, prompt]

        response_text = self._call_api(parts, max_tokens=512)
        return self._parse_action_response(response_text)

    def extract_data(
        self,
        screenshot_bytes: bytes,
        fields_to_extract: list,
    ) -> dict:
        """Extract data fields from a document screenshot."""
        fields_list = "\n".join([f"- {f}" for f in fields_to_extract])
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(fields_list=fields_list)

        parts = [{"mime_type": "image/png", "data": screenshot_bytes}, prompt]

        response_text = self._call_api(parts, max_tokens=1024)
        return self._parse_extraction_response(response_text)
