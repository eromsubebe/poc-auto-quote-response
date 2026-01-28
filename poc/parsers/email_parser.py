"""Simple .eml parser used by the MVP.

Goal: make the PoC runnable without external/private parsing packages.
This focuses on extracting the 80% "body-only" RFQs:

Extracts:
- Sender name/email (From header)
- Subject
- Plaintext body
- Attachments (bytes + basic document_type classification)
- Lightweight heuristics for urgency, shipping mode, reference number, weight

Later phases can replace this module with richer NLP + PDF extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parseaddr, parsedate_to_datetime
from enum import Enum
from pathlib import Path
from typing import Optional


class ShippingModeEnum(str, Enum):
    AIR = "AIR"
    SEA = "SEA"
    ROAD = "ROAD"


class UrgencyEnum(str, Enum):
    STANDARD = "STANDARD"
    URGENT = "URGENT"


@dataclass
class ExtractedFields:
    reference_number: Optional[str] = None
    shipping_mode: Optional[ShippingModeEnum] = None
    urgency: UrgencyEnum = UrgencyEnum.STANDARD

    origin_country: Optional[str] = None
    origin_address: Optional[str] = None
    destination_country: Optional[str] = None
    destination_port: Optional[str] = None

    total_weight_kg: Optional[float] = None

    # Optional fields (not yet extracted in MVP)
    special_instructions: Optional[str] = None
    total_pieces: Optional[int] = None
    cargo_packages: list["CargoPackage"] = None  # type: ignore[assignment]


@dataclass
class CargoPackage:
    quantity: Optional[int] = None
    package_type: Optional[str] = None
    length_cm: Optional[float] = None
    width_cm: Optional[float] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    description: Optional[str] = None


@dataclass
class Attachment:
    filename: str
    content_type: str
    content: bytes
    document_type: str  # "CIPL", "MSDS", "OTHER"
    size_bytes: int


@dataclass
class ParsedEmail:
    message_id: Optional[str]
    from_name: Optional[str]
    from_email: Optional[str]
    from_company: Optional[str]
    to: list[str]
    cc: list[str]
    subject: str
    body_text: str
    received_at: Optional[datetime]
    importance: Optional[str]
    attachments: list[Attachment]
    extracted_fields: ExtractedFields


_REF_PATTERNS = [
    # e.g. OA/PO/BC-0000966
    re.compile(r"\b[A-Z]{2,5}/[A-Z]{2,5}/[A-Z]{2,5}-\d{4,}\b"),
    # generic PO style
    re.compile(r"\b(?:PO|P\.O\.|RFQ|REF)\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/]{5,})\b", re.IGNORECASE),
]

_WEIGHT_KG = re.compile(r"\b(\d+(?:\.\d+)?)\s*(kg|kgs|kilogram|kilograms)\b", re.IGNORECASE)


def _classify_document_type(filename: str, content_type: str) -> str:
    n = (filename or "").lower()
    ct = (content_type or "").lower()

    if "msds" in n or "sds" in n:
        return "MSDS"
    if any(k in n for k in ["invoice", "packing", "cipl", "c\s?i\s?p\s?l", "pl", "commercial"]):
        return "CIPL"

    # weak heuristic: some customers send MSDS as unnamed PDFs
    if ct == "application/pdf" and "msds" in n:
        return "MSDS"

    return "OTHER"


def _guess_mode(text: str) -> Optional[ShippingModeEnum]:
    t = (text or "").lower()
    if any(k in t for k in ["air freight", "air shipment", "by air", "iata", "lhr", "airway bill", "awb"]):
        return ShippingModeEnum.AIR
    if any(k in t for k in ["sea freight", "ocean", "vessel", "by sea", "container", "bill of lading", "b/l"]):
        return ShippingModeEnum.SEA
    if any(k in t for k in ["by road", "truck", "haulage", "road freight"]):
        return ShippingModeEnum.ROAD
    return None


def _guess_urgency(text: str) -> UrgencyEnum:
    t = (text or "").lower()
    if any(k in t for k in ["urgent", "asap", "immediately", "priority", "time-critical", "time critical"]):
        return UrgencyEnum.URGENT
    return UrgencyEnum.STANDARD


def _extract_reference(text: str) -> Optional[str]:
    for pat in _REF_PATTERNS:
        m = pat.search(text or "")
        if not m:
            continue
        # first pattern returns full match, second returns group
        if m.lastindex:
            return m.group(1)
        return m.group(0)
    return None


def _extract_total_weight_kg(text: str) -> Optional[float]:
    weights = []
    for m in _WEIGHT_KG.finditer(text or ""):
        try:
            weights.append(float(m.group(1)))
        except ValueError:
            continue
    if not weights:
        return None
    # take the max as a rough estimate of total
    return max(weights)


class EmailParser:
    """Parse an RFC822 .eml file from disk."""

    def parse_file(self, eml_path: str) -> ParsedEmail:
        p = Path(eml_path)
        raw = p.read_bytes()
        msg = BytesParser(policy=policy.default).parsebytes(raw)

        # From
        from_header = msg.get("From", "")
        from_name, from_email = parseaddr(from_header)
        from_name = from_name.strip() or None
        from_email = from_email.strip() or None

        # Message metadata
        message_id = (msg.get("Message-ID", "") or "").strip() or None

        # To / CC
        to_addrs = [a for _, a in getaddresses(msg.get_all("To", [])) if a]
        cc_addrs = [a for _, a in getaddresses(msg.get_all("Cc", [])) if a]

        # Date
        received_at: Optional[datetime] = None
        date_header = (msg.get("Date", "") or "").strip()
        if date_header:
            try:
                received_at = parsedate_to_datetime(date_header)
            except Exception:
                received_at = None

        # Importance / priority
        importance = (msg.get("Importance", "") or "").strip() or None
        if not importance:
            # Some clients use X-Priority
            importance = (msg.get("X-Priority", "") or "").strip() or None

        # Subject
        subject = (msg.get("Subject", "") or "").strip()

        # Body (prefer text/plain)
        body_text = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                disp = part.get_content_disposition()
                if disp in ("attachment", "inline"):
                    continue
                if ctype == "text/plain":
                    try:
                        body_text = part.get_content()
                    except Exception:
                        body_text = part.get_payload(decode=True) or b""
                        body_text = body_text.decode(errors="ignore")
                    break
        else:
            try:
                body_text = msg.get_content()
            except Exception:
                payload = msg.get_payload(decode=True) or b""
                body_text = payload.decode(errors="ignore")

        body_text = body_text.strip()

        # Attachments
        attachments: list[Attachment] = []
        if msg.is_multipart():
            for part in msg.walk():
                disp = part.get_content_disposition()
                if disp != "attachment":
                    continue
                filename = part.get_filename() or "attachment"
                content_type = part.get_content_type() or "application/octet-stream"
                content = part.get_payload(decode=True) or b""
                doc_type = _classify_document_type(filename, content_type)
                attachments.append(
                    Attachment(
                        filename=filename,
                        content_type=content_type,
                        content=content,
                        document_type=doc_type,
                        size_bytes=len(content),
                    )
                )

        # Simple heuristic extraction
        combined = f"{subject}\n\n{body_text}"
        ef = ExtractedFields(
            reference_number=_extract_reference(combined),
            shipping_mode=_guess_mode(combined),
            urgency=_guess_urgency(combined),
            total_weight_kg=_extract_total_weight_kg(combined),
        )

        # Company name: in MVP we infer from the from_name if it looks like a company
        from_company = None
        if from_name and any(tok in from_name.lower() for tok in ["ltd", "limited", "inc", "company", "co."]):
            from_company = from_name

        if ef.cargo_packages is None:
            ef.cargo_packages = []

        return ParsedEmail(
            message_id=message_id,
            from_name=from_name,
            from_email=from_email,
            from_company=from_company,
            to=to_addrs,
            cc=cc_addrs,
            subject=subject,
            body_text=body_text,
            received_at=received_at,
            importance=importance,
            attachments=attachments,
            extracted_fields=ef,
        )
