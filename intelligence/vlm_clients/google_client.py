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
    DOC_VERIFICATION_PROMPT_TEMPLATE,
    VLMUsage,
)
from typing import Tuple, Dict, Any


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

    def _call_api(self, parts: list, max_tokens: int = 1024) -> Tuple[str, VLMUsage]:
        """Make API call to Google Gemini and return (content, usage)."""
        generation_config = self.genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.1,
        )
        response = self.model.generate_content(
            parts, generation_config=generation_config
        )
        
        usage = VLMUsage(model_id=self.model_id)
        if hasattr(response, 'usage_metadata'):
            usage.input_tokens = response.usage_metadata.prompt_token_count
            usage.output_tokens = response.usage_metadata.candidates_token_count
            
        return response.text, usage

    def analyze_and_act(
        self,
        screenshot_bytes: bytes,
        task_description: str,
        context: dict,
        image_width: int,
        image_height: int,
    ) -> Tuple[VLMAction, VLMUsage]:
        """Analyze screenshot and determine next action."""
        prompt = ACTION_PROMPT_TEMPLATE.format(
            applicant_data=json.dumps(context.get("applicant_data", {}), indent=2),
            task_description=task_description,
            width=image_width,
            height=image_height,
        )

        parts = [{"mime_type": "image/png", "data": screenshot_bytes}, prompt]

        response_text, usage = self._call_api(parts, max_tokens=512)
        return self._parse_action_response(response_text), usage

    def extract_data(
        self,
        screenshot_bytes: bytes,
        fields_to_extract: list,
    ) -> Tuple[Dict[str, str], VLMUsage]:
        """Extract data fields from a document screenshot."""
        fields_list = "\n".join([f"- {f}" for f in fields_to_extract])
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(fields_list=fields_list)

        parts = [{"mime_type": "image/png", "data": screenshot_bytes}, prompt]

        response_text, usage = self._call_api(parts, max_tokens=1024)
        return self._parse_extraction_response(response_text), usage

    def analyze_document(
        self,
        screenshot_bytes: bytes,
        validation_prompt: str,
    ) -> Tuple[Dict[str, Any], VLMUsage]:
        """Analyze a document for validation purposes using a custom prompt."""
        parts = [{"mime_type": "image/png", "data": screenshot_bytes}, validation_prompt]
        response_text, usage = self._call_api(parts, max_tokens=2048)
        return self._parse_extraction_response(response_text), usage

    def describe_document(self, screenshot_bytes: bytes) -> Tuple[str, VLMUsage]:
        """Get a text description of what's in a document screenshot."""
        prompt = "Describe this insurance document screenshot in detail. What type of document is it? What key information (names, numbers, dates) is visible? Be specific."
        parts = [{"mime_type": "image/png", "data": screenshot_bytes}, prompt]
        return self._call_api(parts, max_tokens=512)

    def verify_document(
        self,
        screenshot_bytes: bytes,
        doc_type: str,
        applicant_data: dict,
        questions: dict,
    ) -> Tuple[Dict[str, Any], VLMUsage]:
        """Verify a scanned document screenshot against applicant data."""
        questions_json = ",\n".join(
            f'  "{qid}": true/false or "extracted_value"  // {qtext}'
            for qid, qtext in questions.items()
        )

        prompt = DOC_VERIFICATION_PROMPT_TEMPLATE.format(
            doc_type=doc_type,
            applicant_data=json.dumps(applicant_data, indent=2),
            questions_json=questions_json,
        )

        parts = [{"mime_type": "image/png", "data": screenshot_bytes}, prompt]
        response_text, usage = self._call_api(parts, max_tokens=1024)
        return self._parse_extraction_response(response_text), usage
