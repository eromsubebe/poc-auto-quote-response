"""Gemini AI-powered RFQ field extraction using Vertex AI.

This module provides intelligent extraction of RFQ fields from email content
and attachments using Google's Gemini model via Vertex AI.
"""

import base64
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from poc.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeminiExtractionResult:
    """Result from Gemini AI extraction."""

    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_company: Optional[str] = None
    reference_number: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    shipping_mode: Optional[str] = None  # AIR, SEA, ROAD
    urgency: str = "STANDARD"  # STANDARD or URGENT
    cargo_summary: Optional[str] = None
    total_weight_kg: Optional[float] = None
    total_pieces: Optional[int] = None
    is_dangerous_goods: bool = False
    special_instructions: Optional[str] = None
    confidence_score: float = 0.0
    raw_response: Optional[str] = None
    error: Optional[str] = None


EXTRACTION_PROMPT = """You are an expert freight forwarding assistant. Analyze this RFQ (Request for Quote) email and extract the following information.

Return ONLY a valid JSON object with these fields (use null for missing values):
{
    "customer_name": "Full name of the person sending the RFQ",
    "customer_email": "Email address of sender",
    "customer_company": "Company name of the customer",
    "reference_number": "Any PO number, order reference, or RFQ reference",
    "origin": "Origin location/port/country (pickup location)",
    "destination": "Destination location/port/country (delivery location)",
    "shipping_mode": "AIR, SEA, or ROAD (choose one based on context)",
    "urgency": "URGENT if time-critical mentioned, otherwise STANDARD",
    "cargo_summary": "Brief description of the cargo being shipped",
    "total_weight_kg": numeric value or null,
    "total_pieces": numeric value or null,
    "is_dangerous_goods": true if chemicals/hazardous materials mentioned, otherwise false,
    "special_instructions": "Any special handling requirements mentioned",
    "confidence_score": 0.0 to 1.0 based on how confident you are in the extraction
}

Important guidelines:
- For shipping_mode: Look for keywords like "air freight", "sea freight", "ocean", "road", "truck"
- For urgency: Look for "urgent", "ASAP", "priority", "time-critical"
- For dangerous goods: Look for MSDS, chemicals, UN numbers, hazmat references
- Port codes: SIN=Singapore, PHC=Port Harcourt, LOS=Lagos, LHR=London Heathrow
- Extract exact values when available, don't guess numeric values

Email content:
"""


class GeminiExtractor:
    """Extract RFQ fields using Google Gemini via Vertex AI."""

    def __init__(self):
        self._client = None
        self._model = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Lazily initialize Vertex AI client."""
        if self._initialized:
            return self._client is not None

        self._initialized = True

        if not settings.gemini_enabled:
            logger.info("Gemini extraction disabled (no credentials configured)")
            return False

        try:
            import vertexai
            from vertexai.generative_models import GenerativeModel

            vertexai.init(
                project=settings.GCP_PROJECT_ID,
                location=settings.GCP_REGION,
            )

            self._model = GenerativeModel(settings.GEMINI_MODEL)
            self._client = True  # Mark as initialized
            logger.info(f"Gemini extractor initialized with model {settings.GEMINI_MODEL}")
            return True

        except ImportError:
            logger.warning("google-cloud-aiplatform not installed, Gemini extraction disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            return False

    def extract_from_text(self, email_text: str, subject: str = "") -> GeminiExtractionResult:
        """Extract RFQ fields from email text content.

        Args:
            email_text: The email body text
            subject: The email subject line

        Returns:
            GeminiExtractionResult with extracted fields
        """
        if not self._ensure_initialized():
            return GeminiExtractionResult(
                error="Gemini extraction not available",
                confidence_score=0.0
            )

        try:
            # Prepare prompt with email content
            full_content = f"Subject: {subject}\n\n{email_text}"
            prompt = EXTRACTION_PROMPT + full_content

            response = self._model.generate_content(prompt)

            # Parse the JSON response
            return self._parse_response(response.text)

        except Exception as e:
            logger.error(f"Gemini extraction failed: {e}")
            return GeminiExtractionResult(
                error=str(e),
                confidence_score=0.0
            )

    def extract_from_email_with_attachments(
        self,
        email_text: str,
        subject: str = "",
        attachment_paths: Optional[list[str]] = None
    ) -> GeminiExtractionResult:
        """Extract RFQ fields from email with optional PDF attachments.

        Uses Gemini's multimodal capabilities to analyze PDFs.

        Args:
            email_text: The email body text
            subject: The email subject line
            attachment_paths: List of paths to attachment files (PDFs)

        Returns:
            GeminiExtractionResult with extracted fields
        """
        if not self._ensure_initialized():
            return GeminiExtractionResult(
                error="Gemini extraction not available",
                confidence_score=0.0
            )

        try:
            from vertexai.generative_models import Part

            # Build content parts
            parts = []

            # Add the text prompt
            full_content = f"Subject: {subject}\n\n{email_text}"
            enhanced_prompt = EXTRACTION_PROMPT + full_content

            if attachment_paths:
                enhanced_prompt += "\n\nThe following PDF attachments are also included. Extract any additional information from them:"

            parts.append(Part.from_text(enhanced_prompt))

            # Add PDF attachments as parts
            if attachment_paths:
                for path in attachment_paths[:3]:  # Limit to first 3 attachments
                    file_path = Path(path)
                    if file_path.exists() and file_path.suffix.lower() == '.pdf':
                        try:
                            pdf_bytes = file_path.read_bytes()
                            parts.append(Part.from_data(
                                data=pdf_bytes,
                                mime_type="application/pdf"
                            ))
                            logger.debug(f"Added PDF attachment: {file_path.name}")
                        except Exception as e:
                            logger.warning(f"Could not read attachment {path}: {e}")

            response = self._model.generate_content(parts)

            return self._parse_response(response.text)

        except Exception as e:
            logger.error(f"Gemini extraction with attachments failed: {e}")
            # Fallback to text-only extraction
            return self.extract_from_text(email_text, subject)

    def _parse_response(self, response_text: str) -> GeminiExtractionResult:
        """Parse Gemini's JSON response into extraction result."""
        try:
            # Clean up response - Gemini may wrap JSON in markdown code blocks
            cleaned = response_text.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)

            # Normalize shipping mode
            shipping_mode = data.get("shipping_mode")
            if shipping_mode:
                shipping_mode = shipping_mode.upper()
                if shipping_mode not in ("AIR", "SEA", "ROAD"):
                    shipping_mode = None

            # Normalize urgency
            urgency = data.get("urgency", "STANDARD")
            if urgency not in ("STANDARD", "URGENT"):
                urgency = "URGENT" if "urgent" in str(urgency).lower() else "STANDARD"

            return GeminiExtractionResult(
                customer_name=data.get("customer_name"),
                customer_email=data.get("customer_email"),
                customer_company=data.get("customer_company"),
                reference_number=data.get("reference_number"),
                origin=data.get("origin"),
                destination=data.get("destination"),
                shipping_mode=shipping_mode,
                urgency=urgency,
                cargo_summary=data.get("cargo_summary"),
                total_weight_kg=self._to_float(data.get("total_weight_kg")),
                total_pieces=self._to_int(data.get("total_pieces")),
                is_dangerous_goods=bool(data.get("is_dangerous_goods", False)),
                special_instructions=data.get("special_instructions"),
                confidence_score=float(data.get("confidence_score", 0.5)),
                raw_response=response_text,
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            return GeminiExtractionResult(
                error=f"Invalid JSON response: {e}",
                raw_response=response_text,
                confidence_score=0.0
            )

    @staticmethod
    def _to_float(value) -> Optional[float]:
        """Safely convert value to float."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _to_int(value) -> Optional[int]:
        """Safely convert value to int."""
        if value is None:
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None


# Singleton instance for reuse
_extractor: Optional[GeminiExtractor] = None


def get_gemini_extractor() -> GeminiExtractor:
    """Get the singleton Gemini extractor instance."""
    global _extractor
    if _extractor is None:
        _extractor = GeminiExtractor()
    return _extractor
