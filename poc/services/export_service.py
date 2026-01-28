"""Draft pack export service for generating structured RFQ data for Odoo entry.

This module generates exportable draft packs in JSON and PDF formats
containing all information needed to create a quotation in Cre-soft/Odoo.
"""

import csv
import io
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from poc.db_models import Rate, RFQWorkflow

logger = logging.getLogger(__name__)


@dataclass
class DraftPackExport:
    """Structured draft pack export data."""

    rfq_id: str
    rfq_reference: Optional[str]
    export_format: str  # "json", "csv", "pdf"
    exported_at: str
    data: dict[str, Any]
    raw_bytes: Optional[bytes] = None
    filename: str = ""


def generate_draft_pack(
    db: Session,
    rfq_id: str,
    export_format: str = "json"
) -> DraftPackExport:
    """Generate a draft pack export for an RFQ.

    Args:
        db: Database session
        rfq_id: The RFQ ID to export
        export_format: Output format - "json", "csv", or "pdf"

    Returns:
        DraftPackExport with structured data and optional raw bytes

    Raises:
        ValueError: If RFQ not found or format invalid
    """
    rfq = db.query(RFQWorkflow).filter(RFQWorkflow.id == rfq_id).first()
    if not rfq:
        raise ValueError(f"RFQ not found: {rfq_id}")

    # Build the structured export data
    export_data = _build_export_data(db, rfq)

    exported_at = datetime.utcnow().isoformat() + "Z"
    base_filename = f"draft_pack_{rfq.rfq_reference or rfq_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    if export_format == "json":
        return DraftPackExport(
            rfq_id=rfq_id,
            rfq_reference=rfq.rfq_reference,
            export_format="json",
            exported_at=exported_at,
            data=export_data,
            raw_bytes=json.dumps(export_data, indent=2, default=str).encode("utf-8"),
            filename=f"{base_filename}.json"
        )

    elif export_format == "csv":
        csv_bytes = _generate_csv(export_data)
        return DraftPackExport(
            rfq_id=rfq_id,
            rfq_reference=rfq.rfq_reference,
            export_format="csv",
            exported_at=exported_at,
            data=export_data,
            raw_bytes=csv_bytes,
            filename=f"{base_filename}.csv"
        )

    elif export_format == "pdf":
        pdf_bytes = _generate_pdf(export_data)
        return DraftPackExport(
            rfq_id=rfq_id,
            rfq_reference=rfq.rfq_reference,
            export_format="pdf",
            exported_at=exported_at,
            data=export_data,
            raw_bytes=pdf_bytes,
            filename=f"{base_filename}.pdf"
        )

    else:
        raise ValueError(f"Invalid export format: {export_format}")


def _build_export_data(db: Session, rfq: RFQWorkflow) -> dict[str, Any]:
    """Build structured export data from RFQ record."""
    # Get rate details if assigned
    rate_data = None
    if rfq.rate_id:
        rate = db.query(Rate).filter(Rate.id == rfq.rate_id).first()
        if rate:
            rate_data = {
                "rate_id": rate.id,
                "carrier_name": rate.carrier_name,
                "mode": rate.mode,
                "origin_port": rate.origin_port,
                "destination_port": rate.destination_port,
                "currency": rate.currency,
                "rate_per_unit": rate.rate_per_unit,
                "unit": rate.unit,
                "minimum_charge": rate.minimum_charge,
                "dg_surcharge_pct": rate.dg_surcharge_pct,
                "valid_from": rate.valid_from.isoformat() if rate.valid_from else None,
                "valid_to": rate.valid_to.isoformat() if rate.valid_to else None,
            }

    # Parse stored JSON data
    email_data = json.loads(rfq.parsed_email_json) if rfq.parsed_email_json else None
    cipl_data = json.loads(rfq.parsed_cipl_json) if rfq.parsed_cipl_json else None
    msds_data = json.loads(rfq.parsed_msds_json) if rfq.parsed_msds_json else None

    # Build cargo summary from email and CIPL data
    cargo_summary = _build_cargo_summary(email_data, cipl_data)

    # Build DG classification if applicable
    dg_classification = None
    if rfq.is_dangerous_goods and msds_data:
        dg_classification = _build_dg_classification(msds_data)

    # Build quote line items
    quote_lines = _build_quote_lines(rfq, rate_data)

    return {
        "export_metadata": {
            "rfq_id": rfq.id,
            "rfq_reference": rfq.rfq_reference,
            "status": rfq.status,
            "odoo_quotation_number": rfq.odoo_quotation_number,
        },
        "customer": {
            "name": rfq.customer_name,
            "email": rfq.customer_email,
            "company": email_data.get("from_company") if email_data else None,
        },
        "shipment": {
            "origin": rfq.origin,
            "destination": rfq.destination,
            "shipping_mode": rfq.shipping_mode,
            "urgency": rfq.urgency,
            "is_dangerous_goods": rfq.is_dangerous_goods,
        },
        "cargo_summary": cargo_summary,
        "dg_classification": dg_classification,
        "rate": rate_data,
        "quote_lines": quote_lines,
        "totals": {
            "estimated_cost": rfq.estimated_cost,
            "currency": rfq.rate_currency or "USD",
        },
        "timestamps": {
            "received_at": rfq.received_at.isoformat() if rfq.received_at else None,
            "parsing_completed_at": rfq.parsing_completed_at.isoformat() if rfq.parsing_completed_at else None,
            "rate_found_at": rfq.rate_found_at.isoformat() if rfq.rate_found_at else None,
            "quote_drafted_at": rfq.quote_drafted_at.isoformat() if rfq.quote_drafted_at else None,
        },
        "raw_data": {
            "email": email_data,
            "cipl": cipl_data,
            "msds": msds_data,
        },
    }


def _build_cargo_summary(email_data: Optional[dict], cipl_data: Optional[dict]) -> dict:
    """Build cargo summary from parsed data."""
    summary = {
        "items": [],
        "total_weight_kg": None,
        "total_pieces": None,
        "total_value": None,
        "currency": None,
        "hs_codes": [],
        "country_of_origin": None,
    }

    if email_data and email_data.get("extracted_fields"):
        ef = email_data["extracted_fields"]
        summary["total_weight_kg"] = ef.get("total_weight_kg")
        summary["total_pieces"] = ef.get("total_pieces")

        # Add cargo packages from email
        for pkg in ef.get("cargo_packages", []):
            summary["items"].append({
                "description": pkg.get("description"),
                "quantity": pkg.get("quantity"),
                "package_type": pkg.get("package_type"),
                "dimensions": {
                    "length_cm": pkg.get("length_cm"),
                    "width_cm": pkg.get("width_cm"),
                    "height_cm": pkg.get("height_cm"),
                },
                "weight_kg": pkg.get("weight_kg"),
            })

    if cipl_data:
        summary["total_value"] = cipl_data.get("total_value")
        summary["currency"] = cipl_data.get("currency")
        summary["hs_codes"] = cipl_data.get("hs_codes", [])
        summary["country_of_origin"] = cipl_data.get("country_of_origin")

        # Override weights from CIPL if available (more authoritative)
        if cipl_data.get("total_gross_weight_kg"):
            summary["total_weight_kg"] = cipl_data["total_gross_weight_kg"]

    return summary


def _build_dg_classification(msds_data: list[dict] | dict) -> dict:
    """Build dangerous goods classification from MSDS data."""
    # Handle both list and single dict
    msds_list = msds_data if isinstance(msds_data, list) else [msds_data]

    products = []
    for msds in msds_list:
        products.append({
            "product_name": msds.get("product_name"),
            "product_code": msds.get("product_code"),
            "ghs_symbols": msds.get("ghs_symbols", []),
            "h_statements": msds.get("h_statements", []),
            "air_transport": {
                "iata_class": msds.get("iata_class"),
                "iata_packing_group": msds.get("iata_packing_group"),
                "un_number": msds.get("iata_un_number"),
            },
            "sea_transport": {
                "imo_class": msds.get("imo_class"),
                "un_number": msds.get("imo_un_number"),
            },
        })

    return {
        "is_dangerous_goods": True,
        "products": products,
        "special_handling_required": True,
        "dg_surcharge_applicable": True,
    }


def _build_quote_lines(rfq: RFQWorkflow, rate_data: Optional[dict]) -> list[dict]:
    """Build quote line items for Odoo entry."""
    lines = []

    if rate_data and rfq.estimated_cost:
        # Main freight line
        lines.append({
            "line_type": "freight",
            "description": f"{rate_data['mode']} Freight - {rate_data['carrier_name']}",
            "route": f"{rate_data['origin_port']} → {rate_data['destination_port']}",
            "quantity": 1,
            "unit_price": rfq.estimated_cost,
            "currency": rfq.rate_currency or "USD",
            "subtotal": rfq.estimated_cost,
        })

        # DG surcharge line if applicable
        if rfq.is_dangerous_goods and rate_data.get("dg_surcharge_pct"):
            surcharge_pct = rate_data["dg_surcharge_pct"]
            surcharge_amount = rfq.estimated_cost * (surcharge_pct / 100)
            lines.append({
                "line_type": "surcharge",
                "description": f"Dangerous Goods Surcharge ({surcharge_pct}%)",
                "quantity": 1,
                "unit_price": surcharge_amount,
                "currency": rfq.rate_currency or "USD",
                "subtotal": surcharge_amount,
            })

    return lines


def _generate_csv(export_data: dict) -> bytes:
    """Generate CSV export from structured data."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header section
    writer.writerow(["RFQ Draft Pack Export"])
    writer.writerow([])

    # Metadata
    writer.writerow(["METADATA"])
    meta = export_data["export_metadata"]
    writer.writerow(["RFQ ID", meta["rfq_id"]])
    writer.writerow(["Reference", meta["rfq_reference"]])
    writer.writerow(["Status", meta["status"]])
    writer.writerow(["Odoo Quote #", meta["odoo_quotation_number"]])
    writer.writerow([])

    # Customer
    writer.writerow(["CUSTOMER"])
    cust = export_data["customer"]
    writer.writerow(["Name", cust["name"]])
    writer.writerow(["Email", cust["email"]])
    writer.writerow(["Company", cust["company"]])
    writer.writerow([])

    # Shipment
    writer.writerow(["SHIPMENT"])
    ship = export_data["shipment"]
    writer.writerow(["Origin", ship["origin"]])
    writer.writerow(["Destination", ship["destination"]])
    writer.writerow(["Mode", ship["shipping_mode"]])
    writer.writerow(["Urgency", ship["urgency"]])
    writer.writerow(["Dangerous Goods", "Yes" if ship["is_dangerous_goods"] else "No"])
    writer.writerow([])

    # Cargo
    writer.writerow(["CARGO"])
    cargo = export_data["cargo_summary"]
    writer.writerow(["Total Weight (kg)", cargo["total_weight_kg"]])
    writer.writerow(["Total Pieces", cargo["total_pieces"]])
    writer.writerow(["Total Value", f"{cargo['currency'] or ''} {cargo['total_value'] or ''}"])
    writer.writerow(["HS Codes", ", ".join(cargo["hs_codes"]) if cargo["hs_codes"] else ""])
    writer.writerow([])

    # Quote Lines
    writer.writerow(["QUOTE LINES"])
    writer.writerow(["Type", "Description", "Quantity", "Unit Price", "Currency", "Subtotal"])
    for line in export_data["quote_lines"]:
        writer.writerow([
            line["line_type"],
            line["description"],
            line["quantity"],
            line["unit_price"],
            line["currency"],
            line["subtotal"],
        ])
    writer.writerow([])

    # Totals
    writer.writerow(["TOTALS"])
    totals = export_data["totals"]
    writer.writerow(["Estimated Cost", f"{totals['currency']} {totals['estimated_cost']}"])

    return output.getvalue().encode("utf-8")


def _generate_pdf(export_data: dict) -> bytes:
    """Generate PDF export from structured data."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError:
        logger.warning("reportlab not installed, returning JSON as fallback")
        return json.dumps(export_data, indent=2, default=str).encode("utf-8")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=20,
    )
    elements.append(Paragraph("RFQ Draft Pack", title_style))

    # Metadata section
    meta = export_data["export_metadata"]
    meta_data = [
        ["RFQ ID:", meta["rfq_id"]],
        ["Reference:", meta["rfq_reference"] or "-"],
        ["Status:", meta["status"]],
        ["Odoo Quote #:", meta["odoo_quotation_number"] or "-"],
    ]
    meta_table = Table(meta_data, colWidths=[4*cm, 12*cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 20))

    # Customer section
    elements.append(Paragraph("Customer Details", styles["Heading2"]))
    cust = export_data["customer"]
    cust_data = [
        ["Name:", cust["name"] or "-"],
        ["Email:", cust["email"] or "-"],
        ["Company:", cust["company"] or "-"],
    ]
    cust_table = Table(cust_data, colWidths=[4*cm, 12*cm])
    cust_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(cust_table)
    elements.append(Spacer(1, 20))

    # Shipment section
    elements.append(Paragraph("Shipment Details", styles["Heading2"]))
    ship = export_data["shipment"]
    ship_data = [
        ["Origin:", ship["origin"] or "-"],
        ["Destination:", ship["destination"] or "-"],
        ["Mode:", ship["shipping_mode"] or "-"],
        ["Urgency:", ship["urgency"]],
        ["Dangerous Goods:", "Yes" if ship["is_dangerous_goods"] else "No"],
    ]
    ship_table = Table(ship_data, colWidths=[4*cm, 12*cm])
    ship_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(ship_table)
    elements.append(Spacer(1, 20))

    # Cargo summary
    elements.append(Paragraph("Cargo Summary", styles["Heading2"]))
    cargo = export_data["cargo_summary"]
    cargo_data = [
        ["Total Weight:", f"{cargo['total_weight_kg'] or '-'} kg"],
        ["Total Pieces:", str(cargo["total_pieces"] or "-")],
        ["Total Value:", f"{cargo['currency'] or ''} {cargo['total_value'] or '-'}"],
        ["HS Codes:", ", ".join(cargo["hs_codes"]) if cargo["hs_codes"] else "-"],
    ]
    cargo_table = Table(cargo_data, colWidths=[4*cm, 12*cm])
    cargo_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(cargo_table)
    elements.append(Spacer(1, 20))

    # Quote lines
    if export_data["quote_lines"]:
        elements.append(Paragraph("Quote Lines", styles["Heading2"]))
        quote_header = ["Description", "Qty", "Unit Price", "Subtotal"]
        quote_data = [quote_header]
        for line in export_data["quote_lines"]:
            quote_data.append([
                line["description"],
                str(line["quantity"]),
                f"{line['currency']} {line['unit_price']:.2f}",
                f"{line['currency']} {line['subtotal']:.2f}",
            ])

        quote_table = Table(quote_data, colWidths=[8*cm, 2*cm, 3*cm, 3*cm])
        quote_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ]))
        elements.append(quote_table)
        elements.append(Spacer(1, 20))

    # Totals
    totals = export_data["totals"]
    if totals["estimated_cost"]:
        elements.append(Paragraph(
            f"<b>Total Estimated Cost: {totals['currency']} {totals['estimated_cost']:.2f}</b>",
            styles["Normal"]
        ))

    doc.build(elements)
    return buffer.getvalue()
