"""
Base VLM client interface.
All VLM clients implement this interface.
"""

import base64
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
from PIL import Image
import io


@dataclass
class VLMAction:
    """Represents an action returned by the VLM."""

    action: str  # "click", "type", "select", "scroll", "done", "wait"
    x: Optional[int] = None
    y: Optional[int] = None
    text: Optional[str] = None
    element_id: Optional[str] = None  # DOM element ID for API-based clicks
    element_description: str = ""
    reasoning: str = ""
    confidence: float = 1.0

    def to_dict(self):
        return {
            "action": self.action,
            "x": self.x,
            "y": self.y,
            "text": self.text,
            "element_id": self.element_id,
            "element_description": self.element_description,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }


@dataclass
class ExtractedData:
    """Data extracted from a document screenshot."""

    field_name: str
    value: str
    confidence: float = 1.0
    source: str = ""


def encode_image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def encode_bytes_to_base64(image_bytes: bytes) -> str:
    """Convert raw image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode("utf-8")


class BaseVLMClient(ABC):
    """Base class for VLM clients."""

    def __init__(self, model_id: str, api_key: str):
        self.model_id = model_id
        self.api_key = api_key

    @abstractmethod
    def analyze_and_act(
        self,
        screenshot_bytes: bytes,
        task_description: str,
        context: dict,
        image_width: int,
        image_height: int,
    ) -> VLMAction:
        """
        Analyze a screenshot and determine the next action to take.
        Returns a VLMAction with coordinates and action type.
        """
        pass

    @abstractmethod
    def extract_data(
        self,
        screenshot_bytes: bytes,
        fields_to_extract: list[str],
    ) -> dict[str, str]:
        """
        Extract specific data fields from a document screenshot.
        Returns a dict mapping field names to extracted values.
        """
        pass

    @abstractmethod
    def analyze_document(
        self,
        screenshot_bytes: bytes,
        validation_prompt: str,
    ) -> dict:
        """
        Analyze a document for validation purposes using a custom prompt.
        Returns a dict with validation results.
        """
        pass

    def _parse_action_response(self, response_text: str) -> VLMAction:
        """Parse VLM response text into a VLMAction object."""
        # Try to extract JSON from response
        text = response_text.strip()

        # Look for JSON block
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "{" in text:
            # Find first { and last }
            start = text.find("{")
            end = text.rfind("}") + 1
            text = text[start:end]

        try:
            data = json.loads(text)
            return VLMAction(
                action=data.get("action", "done"),
                x=data.get("x"),
                y=data.get("y"),
                text=data.get("text"),
                element_id=data.get("element_id"),
                element_description=data.get("element_description", ""),
                reasoning=data.get("reasoning", ""),
                confidence=data.get("confidence", 1.0),
            )
        except json.JSONDecodeError:
            # Fallback: try to parse simple text responses
            if "done" in response_text.lower():
                return VLMAction(action="done", reasoning=response_text)
            return VLMAction(
                action="wait",
                reasoning=f"Could not parse response: {response_text[:200]}",
            )

    def _parse_extraction_response(self, response_text: str) -> dict:
        """Parse VLM data extraction response."""
        text = response_text.strip()

        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            text = text[start:end].strip()
        elif "{" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            text = text[start:end]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Return raw text for debugging if parsing fails
            return {"parsing_error": True, "raw_response": response_text}


SYSTEM_PROMPT = """You are an intelligent underwriting automation agent for an insurance company.
Your job is to automate the manual tasks of an underwriting agent by:
1. Extracting information from insurance application documents (PAN card, Aadhaar, bank statements, proposal forms)
2. Filling out the underwriting checklist by clicking Yes/No buttons and entering data in text fields
3. Cross-verifying document data against the application records

You work by analyzing screenshots of web applications and determining what action to take next.
Always return precise, actionable responses in the requested JSON format.
Be methodical and accurate - insurance underwriting decisions have real consequences."""


ACTION_PROMPT_TEMPLATE = """You are analyzing a screenshot of the underwriting checklist application.

APPLICANT DATA (from sales agent application):
{applicant_data}

CURRENT TASK: {task_description}

IMAGE SIZE: {width} x {height} pixels

Based on the screenshot, determine the SINGLE next action to perform.
Look for:
- Unfilled Yes/No button groups (click the appropriate button)
- Empty text input fields (type the correct value)
- Uncomplete dropdown fields (select the correct option)

Return ONLY a valid JSON object (no other text):
{{
  "action": "click" | "type" | "select" | "scroll_down" | "done",
  "x": <pixel x coordinate of the element center, integer>,
  "y": <pixel y coordinate of the element center, integer>,
  "text": "<text to type if action is type or select>",
  "element_id": "<HTML element ID if visible>",
  "element_description": "<what you are clicking/typing in>",
  "reasoning": "<1-2 sentence explanation>",
  "confidence": <0.0 to 1.0>
}}

If all visible fields are filled and you need to scroll to see more, use action "scroll_down".
If the entire form appears complete, use action "done".
"""

EXTRACTION_PROMPT_TEMPLATE = """You are analyzing a screenshot of an insurance document.

Extract the following fields from the document:
{fields_list}

Look carefully at all text in the image. Return ONLY a valid JSON object:
{{
  "field_name_1": "extracted_value_or_empty_string",
  "field_name_2": "extracted_value_or_empty_string",
  ...
}}

Rules:
- For PAN numbers: format as AAAAA9999A (10 characters)
- For Aadhaar numbers: format as XXXX XXXX XXXX (12 digits with spaces)
- For dates: format as DD/MM/YYYY
- For amounts: return numeric value only (no commas or currency symbols)
- If a field is not visible or cannot be read, return empty string ""
"""

DOC_VERIFICATION_PROMPT_TEMPLATE = """You are an insurance underwriting agent verifying a scanned document.

DOCUMENT TYPE: {doc_type}

APPLICANT DATA ON FILE:
{applicant_data}

Carefully examine the document screenshot and answer each verification question.
Return ONLY a valid JSON object:
{{
{questions_json}
}}

Rules:
- Answer true ONLY if the information is clearly visible and matches the applicant data.
- Answer false if the document is missing, unreadable, or the data does not match.
- For extracted values, return the exact text visible in the document.
- Be strict: partial matches or unclear text should be marked false.
"""
