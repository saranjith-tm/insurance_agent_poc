"""
OpenAI VLM Client - supports GPT-4o and GPT-4-vision models.
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


class OpenAIVLMClient(BaseVLMClient):
    """Client for OpenAI GPT-4o vision API."""

    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def _call_api(self, messages: list, max_tokens: int = 1024) -> str:
        """Make API call to OpenAI."""
        response = self.client.chat.completions.create(
            model=self.model_id,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.1,
        )
        return response.choices[0].message.content

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

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]

        response_text = self._call_api(messages, max_tokens=512)
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

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]

        response_text = self._call_api(messages, max_tokens=1024)
        return self._parse_extraction_response(response_text)

    def analyze_document(
        self,
        screenshot_bytes: bytes,
        validation_prompt: str,
    ) -> dict:
        """Analyze a document for validation purposes using a custom prompt."""
        image_b64 = encode_bytes_to_base64(screenshot_bytes)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                            "detail": "high",
                        },
                    },
                    {"type": "text", "text": validation_prompt},
                ],
            },
        ]

        response_text = self._call_api(messages, max_tokens=2048)
        return self._parse_extraction_response(response_text)
