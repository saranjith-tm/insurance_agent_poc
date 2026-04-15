"""
Anthropic Claude VLM Client - supports Claude 3.5 Sonnet and other Claude vision models.
"""

import json
from .base import (
    BaseVLMClient,
    VLMAction,
    encode_bytes_to_base64,
    SYSTEM_PROMPT,
    ACTION_PROMPT_TEMPLATE,
    EXTRACTION_PROMPT_TEMPLATE,
)


class AnthropicClient(BaseVLMClient):
    """Client for Anthropic Claude vision API."""

    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "anthropic package not installed. Run: pip install anthropic"
            )

    def _call_api(self, content: list, max_tokens: int = 1024) -> str:
        """Make API call to Anthropic."""
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        return response.content[0].text

    def analyze_and_act(
        self,
        screenshot_bytes: bytes,
        task_description: str,
        context: dict,
        image_width: int,
        image_height: int,
    ) -> VLMAction:
        """Analyze screenshot and determine next action."""
        image_b64 = encode_bytes_to_base64(screenshot_bytes)

        prompt = ACTION_PROMPT_TEMPLATE.format(
            applicant_data=json.dumps(context.get("applicant_data", {}), indent=2),
            task_description=task_description,
            width=image_width,
            height=image_height,
        )

        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            },
            {"type": "text", "text": prompt},
        ]

        response_text = self._call_api(content, max_tokens=512)
        return self._parse_action_response(response_text)

    def extract_data(
        self,
        screenshot_bytes: bytes,
        fields_to_extract: list,
    ) -> dict:
        """Extract data fields from a document screenshot."""
        image_b64 = encode_bytes_to_base64(screenshot_bytes)

        fields_list = "\n".join([f"- {f}" for f in fields_to_extract])
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(fields_list=fields_list)

        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            },
            {"type": "text", "text": prompt},
        ]

        response_text = self._call_api(content, max_tokens=1024)
        return self._parse_extraction_response(response_text)

    def analyze_document(
        self,
        screenshot_bytes: bytes,
        validation_prompt: str,
    ) -> dict:
        """Analyze a document for validation purposes using a custom prompt."""
        image_b64 = encode_bytes_to_base64(screenshot_bytes)

        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": image_b64,
                },
            },
            {"type": "text", "text": validation_prompt},
        ]

        response_text = self._call_api(content, max_tokens=2048)
        return self._parse_extraction_response(response_text)
