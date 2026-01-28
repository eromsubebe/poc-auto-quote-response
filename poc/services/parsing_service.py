import json
from pathlib import Path

from poc.config import settings
from poc.services.storage import persist_attachment_bytes


def parse_email_file(eml_path: str | Path, rfq_id: str) -> dict:
    """Parse an .eml file and extract all available data.

    Returns a consolidated dict with:
      - email_data: serialized parsed email fields
      - cipl_data: serialized CIPL data (if attachment found)
      - msds_data: serialized MSDS data (if attachment found)
      - customer_name, customer_email, subject
      - shipping_mode, origin, destination
      - is_dangerous_goods, urgency
      - reference
      - attachment_paths: list of saved attachment file paths
      - total_weight_kg: from email body cargo extraction
      - gemini_extraction: Gemini AI extraction result (if enabled)
      - extraction_method: "gemini" or "rule_based"
    """
    # Lightweight in-repo .eml parsing (keeps the MVP self-contained)
    from poc.parsers.email_parser import EmailParser

    parser = EmailParser()
    parsed = parser.parse_file(str(eml_path))

    # Persist attachments and keep a local copy for parsing
    attachment_refs: list[str] = []  # may contain local paths or gs:// URIs
    attachment_local_paths: list[str] = []
    cipl_data = None
    msds_list: list[dict] = []

    for att in parsed.attachments:
        local_path, persisted_ref = persist_attachment_bytes(rfq_id, att.filename, att.content)
        attachment_refs.append(persisted_ref)
        attachment_local_paths.append(str(local_path))

        # MVP note:
        # - We persist and classify attachments, but we do not do heavy PDF parsing here.
        # - For a later phase, add CIPL/MSDS PDF extraction and structured line-item parsing.
        if att.document_type == "CIPL":
            cipl_data = {"filename": att.filename, "stored_ref": persisted_ref}
        if att.document_type == "MSDS":
            msds_list.append({"filename": att.filename, "stored_ref": persisted_ref})

    # Determine DG status using lightweight heuristics (MVP)
    is_dg = False
    if any(a.document_type == "MSDS" for a in parsed.attachments):
        is_dg = True
    body_l = (parsed.body_text or "").lower()
    if any(k in body_l for k in ["msds", "dangerous goods", "hazmat", "hazard", "un "]):
        is_dg = True

    # Extract fields from parsed email (rule-based)
    ef = parsed.extracted_fields
    shipping_mode = ef.shipping_mode.value if ef.shipping_mode else None
    origin = ef.origin_country or ef.origin_address
    destination = ef.destination_port or ef.destination_country

    # Rule-based extraction result
    result = {
        "email_data": _email_to_dict(parsed),
        "cipl_data": cipl_data,
        "msds_data": msds_list if msds_list else None,
        "customer_name": parsed.from_name or parsed.from_company,
        "customer_email": parsed.from_email,
        "subject": parsed.subject,
        "shipping_mode": shipping_mode,
        "origin": origin,
        "destination": destination,
        "is_dangerous_goods": is_dg,
        "urgency": ef.urgency.value if ef.urgency else "STANDARD",
        "reference": ef.reference_number,
        "attachment_paths": attachment_refs,
        "total_weight_kg": ef.total_weight_kg,
        "extraction_method": "rule_based",
        "gemini_extraction": None,
    }

    # Try Gemini AI extraction if enabled
    if settings.gemini_enabled:
        try:
            from poc.services.gemini_extractor import get_gemini_extractor

            extractor = get_gemini_extractor()
            gemini_result = extractor.extract_from_email_with_attachments(
                email_text=parsed.body_text or "",
                subject=parsed.subject or "",
                attachment_paths=attachment_local_paths
            )

            if gemini_result.confidence_score >= 0.5 and not gemini_result.error:
                # Merge Gemini results - prefer Gemini for missing/low-confidence fields
                result["extraction_method"] = "gemini"
                result["gemini_extraction"] = {
                    "confidence_score": gemini_result.confidence_score,
                    "cargo_summary": gemini_result.cargo_summary,
                    "special_instructions": gemini_result.special_instructions,
                }

                # Override rule-based fields if Gemini has better data
                if not result["customer_name"] and gemini_result.customer_name:
                    result["customer_name"] = gemini_result.customer_name
                if not result["shipping_mode"] and gemini_result.shipping_mode:
                    result["shipping_mode"] = gemini_result.shipping_mode
                if not result["origin"] and gemini_result.origin:
                    result["origin"] = gemini_result.origin
                if not result["destination"] and gemini_result.destination:
                    result["destination"] = gemini_result.destination
                if not result["reference"] and gemini_result.reference_number:
                    result["reference"] = gemini_result.reference_number
                if not result["total_weight_kg"] and gemini_result.total_weight_kg:
                    result["total_weight_kg"] = gemini_result.total_weight_kg

                # Gemini urgency detection can be more nuanced
                if gemini_result.urgency == "URGENT":
                    result["urgency"] = "URGENT"

                # Gemini DG detection supplements rule-based MSDS detection
                if gemini_result.is_dangerous_goods:
                    result["is_dangerous_goods"] = True

                logger.info(
                    f"Gemini extraction successful with confidence {gemini_result.confidence_score:.2f}"
                )
            else:
                logger.info(
                    f"Gemini extraction low confidence ({gemini_result.confidence_score:.2f}) "
                    f"or error: {gemini_result.error}, using rule-based"
                )

        except Exception as e:
            logger.warning(f"Gemini extraction failed, falling back to rule-based: {e}")

    return result


def _email_to_dict(parsed) -> dict:
    """Serialize ParsedEmail to JSON-safe dict (excluding binary attachment content)."""
    ef = parsed.extracted_fields
    return {
        "message_id": parsed.message_id,
        "from_name": parsed.from_name,
        "from_email": parsed.from_email,
        "from_company": parsed.from_company,
        "to": parsed.to,
        "cc": parsed.cc,
        "subject": parsed.subject,
        "body_text": parsed.body_text[:2000] if parsed.body_text else None,
        "received_at": parsed.received_at.isoformat() if parsed.received_at else None,
        "importance": parsed.importance,
        "attachment_count": len(parsed.attachments),
        "attachments": [
            {"filename": a.filename, "content_type": a.content_type, "size_bytes": a.size_bytes, "document_type": a.document_type}
            for a in parsed.attachments
        ],
        "extracted_fields": {
            "origin_address": ef.origin_address,
            "origin_country": ef.origin_country,
            "destination_port": ef.destination_port,
            "destination_country": ef.destination_country,
            "reference_number": ef.reference_number,
            "shipping_mode": ef.shipping_mode.value if ef.shipping_mode else None,
            "urgency": ef.urgency.value if ef.urgency else None,
            "special_instructions": ef.special_instructions,
            "total_weight_kg": ef.total_weight_kg,
            "total_pieces": ef.total_pieces,
            "cargo_packages": [
                {
                    "quantity": cp.quantity,
                    "package_type": cp.package_type,
                    "length_cm": cp.length_cm,
                    "width_cm": cp.width_cm,
                    "height_cm": cp.height_cm,
                    "weight_kg": cp.weight_kg,
                    "description": cp.description,
                }
                for cp in ef.cargo_packages
            ],
        },
    }


def _cipl_to_dict(parsed) -> dict:
    """Serialize ParsedCIPL to JSON-safe dict."""
    return {
        "document_number": parsed.document_number,
        "document_date": parsed.document_date.isoformat() if parsed.document_date else None,
        "supplier_name": parsed.supplier_name,
        "consignee_name": parsed.consignee_name,
        "order_reference": parsed.order_reference,
        "currency": parsed.currency,
        "total_value": parsed.total_value,
        "total_gross_weight_kg": parsed.total_gross_weight_kg,
        "total_net_weight_kg": parsed.total_net_weight_kg,
        "line_item_count": len(parsed.line_items),
        "package_count": len(parsed.packages),
        "hs_codes": parsed.hs_codes,
        "country_of_origin": parsed.country_of_origin,
    }


def _msds_to_dict(parsed) -> dict:
    """Serialize ParsedMSDS to JSON-safe dict."""
    return {
        "product_name": parsed.product_name,
        "product_code": parsed.product_code,
        "manufacturer_name": parsed.manufacturer_name,
        "ghs_symbols": parsed.ghs_symbols,
        "h_statements": parsed.h_statements,
        "iata_class": parsed.iata_class,
        "iata_packing_group": parsed.iata_packing_group,
        "iata_un_number": parsed.iata_un_number,
        "imo_class": parsed.imo_class,
        "imo_un_number": parsed.imo_un_number,
    }
