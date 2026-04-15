"""
OpenRouter VLM Client - supports Qwen2.5-VL, Qwen2-VL, Pixtral and other multimodal models.
Primary client for this POC.
"""

import httpx
import json
from .base import (
    BaseVLMClient,
    VLMAction,
    encode_bytes_to_base64,
    SYSTEM_PROMPT,
    ACTION_PROMPT_TEMPLATE,
    EXTRACTION_PROMPT_TEMPLATE,
    DOC_VERIFICATION_PROMPT_TEMPLATE,
)


class OpenRouterClient(BaseVLMClient):
    """Client for OpenRouter API supporting multiple VLM models."""

    API_BASE = "https://openrouter.ai/api/v1"

    def __init__(self, model_id: str, api_key: str):
        super().__init__(model_id, api_key)
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",  # For OpenRouter analytics
            "X-Title": "Insurance UW POC",
        }

    def _call_api(self, messages: list, max_tokens: int = 1024) -> str:
        """Make API call to OpenRouter."""
        payload = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.1,  # Low temperature for deterministic outputs
        }

        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.API_BASE}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                elif "error" in data:
                    raise Exception(f"API error: {data['error']}")
                else:
                    raise Exception(f"Unexpected response format: {data}")

        except httpx.HTTPStatusError as e:
            error_body = e.response.text
            raise Exception(f"HTTP {e.response.status_code}: {error_body}")
        except httpx.TimeoutException:
            raise Exception("API request timed out after 120 seconds")

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

        # Build fields dict for JSON response format
        fields_dict = {f: "" for f in fields_to_extract}
        prompt += f"\n\nRequired JSON structure: {json.dumps(fields_dict, indent=2)}"

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
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
                        },
                    },
                    {"type": "text", "text": validation_prompt},
                ],
            },
        ]

        response_text = self._call_api(messages, max_tokens=2048)
        return self._parse_extraction_response(response_text)

    def describe_document(self, screenshot_bytes: bytes) -> str:
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
    ) -> dict:
        """
        Verify a scanned document screenshot against applicant data.
        questions: dict mapping question_id -> question text (e.g. {"is_uploaded": "Is a PAN card document visible?"})
        Returns: dict mapping question_id -> True/False or extracted string value.
        """
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
                        "image_url": {"url": f"data:image/png;base64,{image_b64}"},
                    },
                    {"type": "text", "text": prompt},
                ],
            },
        ]

        response_text = self._call_api(messages, max_tokens=1024)
        return self._parse_extraction_response(response_text)
