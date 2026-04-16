"""
OpenAI VLM Client - supports GPT-4o and GPT-4-vision models.
"""

import json
import time
from .base import (
    BaseVLMClient,
    VLMAction,
    VLMUsage,
    encode_bytes_to_base64,
    SYSTEM_PROMPT,
    ACTION_PROMPT_TEMPLATE,
    EXTRACTION_PROMPT_TEMPLATE,
    DOC_VERIFICATION_PROMPT_TEMPLATE,
)
from typing import Tuple, Dict, Any


class OpenAIVLMClient(BaseVLMClient):
    """Client for OpenAI GPT-4o vision API."""

    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        try:
            from openai import OpenAI

            self.client = OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")

    def _call_api(self, messages: list, max_tokens: int = 1024) -> Tuple[str, VLMUsage]:
        """Make API call to OpenAI with retry on rate limit and return (content, usage)."""
        from openai import RateLimitError

        max_retries = 5
        delay = 2.0
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_id,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.1,
                )
                usage = VLMUsage(
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    model_id=self.model_id
                )
                return response.choices[0].message.content, usage
            except RateLimitError as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(delay)
                delay *= 2

    def analyze_and_act(
        self,
        screenshot_bytes: bytes,
        task_description: str,
        context: dict,
        image_width: int,
        image_height: int,
    ) -> Tuple[VLMAction, VLMUsage]:
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

        response_text, usage = self._call_api(messages, max_tokens=512)
        return self._parse_action_response(response_text), usage

    def extract_data(
        self,
        screenshot_bytes: bytes,
        fields_to_extract: list,
    ) -> Tuple[Dict[str, str], VLMUsage]:
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

        response_text, usage = self._call_api(messages, max_tokens=1024)
        return self._parse_extraction_response(response_text), usage

    def analyze_document(
        self,
        screenshot_bytes: bytes,
        validation_prompt: str,
    ) -> Tuple[Dict[str, Any], VLMUsage]:
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
                    {"type": "text", "text": prompt if (prompt := validation_prompt) else ""},
                ],
            },
        ]

        response_text, usage = self._call_api(messages, max_tokens=2048)
        return self._parse_extraction_response(response_text), usage

    def describe_document(self, screenshot_bytes: bytes) -> Tuple[str, VLMUsage]:
        """Get a text description of what's in a document screenshot."""
        image_b64 = encode_bytes_to_base64(screenshot_bytes)

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                    {
                        "type": "text",
                        "text": "Describe this insurance document screenshot in detail. What type of document is it? What key information (names, numbers, dates) is visible? Be specific.",
                    },
                ],
            }
        ]

        return self._call_api(messages, max_tokens=512)

    def verify_document(
        self,
        screenshot_bytes: bytes,
        doc_type: str,
        applicant_data: dict,
        questions: dict,
    ) -> Tuple[Dict[str, Any], VLMUsage]:
        """Verify a scanned document screenshot against applicant data."""
        image_b64 = encode_bytes_to_base64(screenshot_bytes)

        questions_json = ",\n".join(
            f'  "{qid}": true/false or "extracted_value"  // {qtext}'
            for qid, qtext in questions.items()
        )

        prompt = DOC_VERIFICATION_PROMPT_TEMPLATE.format(
            doc_type=doc_type,
            applicant_data=json.dumps(applicant_data, indent=2),
            questions_json=questions_json,
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_b64}", "detail": "high"},
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]

        response_text, usage = self._call_api(messages, max_tokens=1024)
        return self._parse_extraction_response(response_text), usage
