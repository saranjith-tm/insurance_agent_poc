"""
Anthropic Claude VLM Client - supports Claude 3.5 Sonnet and other Claude vision models.
"""

import json
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

    def _call_api(self, content: list, max_tokens: int = 1024) -> Tuple[str, VLMUsage]:
        """Make API call to Anthropic and return (content, usage)."""
        response = self.client.messages.create(
            model=self.model_id,
            max_tokens=max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        
        usage = VLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model_id=self.model_id
        )
        return response.content[0].text, usage

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

        response_text, usage = self._call_api(content, max_tokens=512)
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

        response_text, usage = self._call_api(content, max_tokens=1024)
        return self._parse_extraction_response(response_text), usage

    def analyze_document(
        self,
        screenshot_bytes: bytes,
        validation_prompt: str,
    ) -> Tuple[Dict[str, Any], VLMUsage]:
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

        response_text, usage = self._call_api(content, max_tokens=2048)
        return self._parse_extraction_response(response_text), usage

    def describe_document(self, screenshot_bytes: bytes) -> Tuple[str, VLMUsage]:
        """Get a text description of what's in a document screenshot."""
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
            {
                "type": "text",
                "text": "Describe this insurance document screenshot in detail. What type of document is it? What key information (names, numbers, dates) is visible? Be specific.",
            },
        ]

        return self._call_api(content, max_tokens=512)

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

        response_text, usage = self._call_api(content, max_tokens=1024)
        return self._parse_extraction_response(response_text), usage
