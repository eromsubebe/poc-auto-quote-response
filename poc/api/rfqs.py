import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from poc.config import settings
from poc.database import get_db
from poc.schemas import (
    AgentWorkload,
    AssignAgentRequest,
    AssignRateRequest,
    RFQCreateResponse,
    RFQDetail,
    RFQListItem,
    RateLookupRequest,
)
from poc.services import rate_service, workflow_service
from poc.services.mock_odoo import mock_odoo
from poc.services.parsing_service import parse_email_file
from poc.services.storage import persist_email_bytes

router = APIRouter(prefix="/api/rfqs", tags=["rfqs"])


@router.post("/upload", response_model=RFQCreateResponse)
def upload_rfq(email_file: UploadFile, db: Session = Depends(get_db)):
    """Upload an .eml file and run the full RFQ pipeline."""

    # 1) Persist email (GCS when configured) + create temp copy for parsing
    rfq_id = str(uuid.uuid4())
    eml_bytes = email_file.file.read()
    local_eml_path, email_ref = persist_email_bytes(rfq_id, eml_bytes)

    return _run_pipeline(db, rfq_id=rfq_id, eml_path=str(local_eml_path), email_ref=email_ref)


def _run_pipeline(db: Session, rfq_id: str, eml_path: str, email_ref: str) -> RFQCreateResponse:
    """Core pipeline: parse → create RFQ → rate lookup → mock Odoo."""

    # 2. Parse email
    try:
        parsed_data = parse_email_file(eml_path, rfq_id)
    except Exception as e:
        # Even if parsing fails, create a record for tracking
        parsed_data = {
            "customer_name": None,
            "customer_email": None,
            "subject": None,
            "shipping_mode": None,
            "origin": None,
            "destination": None,
            "is_dangerous_goods": False,
            "urgency": "STANDARD",
            "reference": None,
            "email_data": {"error": str(e)},
            "cipl_data": None,
            "msds_data": None,
            "attachment_paths": [],
            "total_weight_kg": None,
        }

    # 3. Create RFQ record
    rfq = workflow_service.create_rfq(db, email_file_path=email_ref, parsed_data=parsed_data)

    # 4. Transition: received → parsing → rates_lookup
    rfq = workflow_service.transition(db, rfq.id, "parsing")
    rfq = workflow_service.transition(db, rfq.id, "rates_lookup")

    # 5. Rate lookup
    message = "Pipeline complete."
    if parsed_data.get("origin") and parsed_data.get("destination") and parsed_data.get("shipping_mode"):
        lookup = rate_service.lookup_rate(
            db,
            RateLookupRequest(
                origin=parsed_data["origin"],
                destination=parsed_data["destination"],
                mode=parsed_data["shipping_mode"],
                weight_kg=parsed_data.get("total_weight_kg"),
                is_dangerous_goods=parsed_data.get("is_dangerous_goods", False),
            ),
        )

        if lookup.found:
            rfq = workflow_service.transition(
                db, rfq.id, "rates_found",
                rate_id=lookup.rate.id,
                rate_amount=lookup.rate.rate_per_unit,
                rate_currency=lookup.rate.currency,
                estimated_cost=lookup.estimated_cost,
            )
            # 6. Create mock Odoo quote
            rfq = workflow_service.transition(db, rfq.id, "quote_draft")
            odoo_result = mock_odoo.create_sale_order({
                "customer_name": rfq.customer_name,
                "reference": rfq.rfq_reference,
                "origin": rfq.origin,
                "destination": rfq.destination,
            })
            rfq.odoo_sale_order_id = odoo_result["sale_order_id"]
            rfq.odoo_quotation_number = odoo_result["quotation_number"]
            db.commit()
            db.refresh(rfq)
            message = f"Rate found ({lookup.match_type}, confidence {lookup.confidence}). Draft quote created: {odoo_result['quotation_number']}"
        else:
            rfq = workflow_service.transition(db, rfq.id, "rates_pending")
            message = f"No rate found for route. Status: rates_pending. {lookup.message}"
    else:
        rfq = workflow_service.transition(db, rfq.id, "rates_pending")
        message = "Incomplete routing info (missing origin/destination/mode). Status: rates_pending."

    return RFQCreateResponse(
        id=rfq.id,
        status=rfq.status,
        customer_name=rfq.customer_name,
        customer_email=rfq.customer_email,
        subject=rfq.subject,
        urgency=rfq.urgency,
        shipping_mode=rfq.shipping_mode,
        origin=rfq.origin,
        destination=rfq.destination,
        is_dangerous_goods=rfq.is_dangerous_goods,
        rate_id=rfq.rate_id,
        rate_amount=rfq.rate_amount,
        rate_currency=rfq.rate_currency,
        estimated_cost=rfq.estimated_cost,
        odoo_sale_order_id=rfq.odoo_sale_order_id,
        odoo_quotation_number=rfq.odoo_quotation_number,
        message=message,
    )


@router.get("", response_model=list[RFQListItem])
def list_rfqs(
    status: str | None = None,
    urgency: str | None = None,
    db: Session = Depends(get_db),
):
    return workflow_service.list_rfqs(db, status=status, urgency=urgency)


@router.get("/{rfq_id}", response_model=RFQDetail)
def get_rfq(rfq_id: str, db: Session = Depends(get_db)):
    rfq = workflow_service.get_rfq(db, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    audit = workflow_service.get_audit_log(db, rfq_id)
    detail = RFQDetail.model_validate(rfq)
    detail.audit_log = [
        {"event": a.event, "old_value": a.old_value, "new_value": a.new_value, "timestamp": a.timestamp.isoformat() if a.timestamp else None}
        for a in audit
    ]
    return detail


@router.post("/{rfq_id}/assign-rate")
def assign_rate(rfq_id: str, body: AssignRateRequest, db: Session = Depends(get_db)):
    """Manually assign a rate to a rates_pending RFQ."""
    rfq = workflow_service.get_rfq(db, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status != "rates_pending":
        raise HTTPException(status_code=400, detail=f"RFQ status is '{rfq.status}', expected 'rates_pending'")

    rate = rate_service.get_rate(db, body.rate_id)
    if not rate:
        raise HTTPException(status_code=404, detail="Rate not found")

    rfq = workflow_service.transition(
        db, rfq_id, "rates_found",
        rate_id=rate.id,
        rate_amount=rate.rate_per_unit,
        rate_currency=rate.currency,
    )

    # Auto-draft quote
    rfq = workflow_service.transition(db, rfq_id, "quote_draft")
    odoo_result = mock_odoo.create_sale_order({
        "customer_name": rfq.customer_name,
        "reference": rfq.rfq_reference,
    })
    rfq.odoo_sale_order_id = odoo_result["sale_order_id"]
    rfq.odoo_quotation_number = odoo_result["quotation_number"]
    db.commit()
    db.refresh(rfq)

    return {
        "id": rfq.id,
        "status": rfq.status,
        "rate_id": rfq.rate_id,
        "odoo_quotation_number": rfq.odoo_quotation_number,
        "message": f"Rate assigned and draft quote created: {odoo_result['quotation_number']}",
    }


@router.post("/{rfq_id}/approve")
def approve_rfq(rfq_id: str, db: Session = Depends(get_db)):
    """Team lead approves → mock Odoo confirm → status=sent."""
    rfq = workflow_service.get_rfq(db, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")
    if rfq.status not in ("quote_draft", "quote_review"):
        raise HTTPException(
            status_code=400,
            detail=f"RFQ status is '{rfq.status}', expected 'quote_draft' or 'quote_review'",
        )

    # Transition to quote_review if currently draft
    if rfq.status == "quote_draft":
        rfq = workflow_service.transition(db, rfq_id, "quote_review")

    # Confirm in mock Odoo
    if rfq.odoo_sale_order_id:
        mock_odoo.confirm_quotation(rfq.odoo_sale_order_id)

    # Transition to sent
    rfq = workflow_service.transition(db, rfq_id, "sent")

    return {
        "id": rfq.id,
        "status": rfq.status,
        "odoo_quotation_number": rfq.odoo_quotation_number,
        "message": "Quote approved and sent.",
    }


@router.patch("/{rfq_id}/assign")
def assign_agent(rfq_id: str, body: AssignAgentRequest, db: Session = Depends(get_db)):
    """Assign an agent to an RFQ for processing.

    This allows team leads to distribute RFQs among pricing team members.
    """
    from poc.db_models import AuditLog, RFQWorkflow

    rfq = workflow_service.get_rfq(db, rfq_id)
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    old_agent = rfq.assigned_agent
    rfq.assigned_agent = body.agent
    db.commit()
    db.refresh(rfq)

    # Log the assignment
    audit = AuditLog(
        rfq_id=rfq_id,
        event="agent_assigned",
        old_value=old_agent,
        new_value=body.agent,
    )
    db.add(audit)
    db.commit()

    return {
        "id": rfq.id,
        "assigned_agent": rfq.assigned_agent,
        "message": f"RFQ assigned to {body.agent}",
    }


@router.get("/agents/workload", response_model=list[AgentWorkload])
def get_agent_workload(db: Session = Depends(get_db)):
    """Get workload summary for all agents with assigned RFQs.

    Returns the count of active and pending RFQs per agent.
    """
    from sqlalchemy import func

    from poc.db_models import RFQWorkflow

    # Active statuses (not yet sent)
    active_statuses = [
        "received", "parsing", "rates_lookup", "rates_pending",
        "rates_found", "quote_draft", "quote_review"
    ]

    # Get agents with their workload
    results = (
        db.query(
            RFQWorkflow.assigned_agent,
            func.count(RFQWorkflow.id).label("total"),
            func.sum(
                func.cast(RFQWorkflow.status.in_(active_statuses), db.bind.dialect.type_descriptor(int) if hasattr(db.bind, 'dialect') else int)
            ).label("active"),
            func.sum(
                func.cast(RFQWorkflow.status == "rates_pending", db.bind.dialect.type_descriptor(int) if hasattr(db.bind, 'dialect') else int)
            ).label("pending"),
        )
        .filter(RFQWorkflow.assigned_agent.isnot(None))
        .group_by(RFQWorkflow.assigned_agent)
        .all()
    )

    return [
        AgentWorkload(
            agent=r[0],
            total_assigned=r[1] or 0,
            active_rfqs=r[2] or 0,
            pending_rfqs=r[3] or 0,
        )
        for r in results
    ]
