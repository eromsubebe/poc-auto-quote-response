"""Export API endpoints for generating draft packs.

Provides endpoints for exporting RFQ data in various formats for Odoo entry.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from poc.database import get_db
from poc.services.export_service import generate_draft_pack

router = APIRouter()


@router.get("/{rfq_id}/export")
def export_rfq(
    rfq_id: str,
    format: str = Query("json", description="Export format: json, csv, or pdf"),
    db: Session = Depends(get_db),
):
    """Export RFQ as a draft pack for Odoo entry.

    Generates a structured export containing:
    - Customer details
    - Shipment information
    - Cargo summary (items, weights, dimensions)
    - Rate details
    - Quote line items
    - DG classification (if applicable)

    Args:
        rfq_id: The RFQ ID to export
        format: Output format - "json" (default), "csv", or "pdf"

    Returns:
        JSON response or file download depending on format
    """
    if format not in ("json", "csv", "pdf"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid format: {format}. Must be one of: json, csv, pdf"
        )

    try:
        export = generate_draft_pack(db, rfq_id, export_format=format)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if format == "json":
        return JSONResponse(content=export.data)

    elif format == "csv":
        return Response(
            content=export.raw_bytes,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"'
            }
        )

    elif format == "pdf":
        return Response(
            content=export.raw_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{export.filename}"'
            }
        )


@router.get("/{rfq_id}/export/preview")
def preview_export(
    rfq_id: str,
    db: Session = Depends(get_db),
):
    """Preview the export data without downloading.

    Returns the structured JSON data that would be included in any export format.
    Useful for reviewing what will be exported before generating a file.

    Args:
        rfq_id: The RFQ ID to preview

    Returns:
        JSON object with all export data
    """
    try:
        export = generate_draft_pack(db, rfq_id, export_format="json")
        return {
            "rfq_id": export.rfq_id,
            "rfq_reference": export.rfq_reference,
            "exported_at": export.exported_at,
            "available_formats": ["json", "csv", "pdf"],
            "data": export.data,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
