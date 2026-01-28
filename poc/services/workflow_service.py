import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from poc.db_models import AuditLog, RFQWorkflow, _uuid, _utcnow

VALID_TRANSITIONS: dict[str, list[str]] = {
    "received": ["parsing"],
    "parsing": ["rates_lookup"],
    "rates_lookup": ["rates_found", "rates_pending"],
    "rates_pending": ["rates_found"],
    "rates_found": ["quote_draft"],
    "quote_draft": ["quote_review"],
    "quote_review": ["sent"],
}

# Map status → timestamp field
STATUS_TIMESTAMP: dict[str, str] = {
    "parsing": "parsing_completed_at",
    "rates_found": "rate_found_at",
    "quote_draft": "quote_drafted_at",
    "sent": "quote_sent_at",
}


class InvalidTransitionError(Exception):
    pass


def create_rfq(
    db: Session,
    email_file_path: str | None = None,
    parsed_data: dict | None = None,
) -> RFQWorkflow:
    from poc.services.sla_monitor import calculate_sla_deadline

    parsed = parsed_data or {}
    received_at = _utcnow()
    urgency = parsed.get("urgency", "STANDARD")

    # Calculate SLA deadline based on urgency
    sla_target_hours, sla_deadline = calculate_sla_deadline(urgency, received_at)

    rfq = RFQWorkflow(
        id=_uuid(),
        rfq_reference=parsed.get("reference"),
        customer_name=parsed.get("customer_name"),
        customer_email=parsed.get("customer_email"),
        subject=parsed.get("subject"),
        status="received",
        shipping_mode=parsed.get("shipping_mode"),
        origin=parsed.get("origin"),
        destination=parsed.get("destination"),
        is_dangerous_goods=parsed.get("is_dangerous_goods", False),
        urgency=urgency,
        parsed_email_json=json.dumps(parsed.get("email_data")) if parsed.get("email_data") else None,
        parsed_cipl_json=json.dumps(parsed.get("cipl_data")) if parsed.get("cipl_data") else None,
        parsed_msds_json=json.dumps(parsed.get("msds_data")) if parsed.get("msds_data") else None,
        email_file_path=email_file_path,
        attachment_paths_json=json.dumps(parsed.get("attachment_paths")) if parsed.get("attachment_paths") else None,
        received_at=received_at,
        # SLA fields
        sla_target_hours=sla_target_hours,
        sla_deadline_at=sla_deadline,
        sla_breached=False,
    )
    db.add(rfq)
    db.commit()
    db.refresh(rfq)
    _write_audit(db, rfq.id, "created", None, "received")
    return rfq


def transition(db: Session, rfq_id: str, new_status: str, **kwargs) -> RFQWorkflow:
    rfq = db.query(RFQWorkflow).filter(RFQWorkflow.id == rfq_id).first()
    if not rfq:
        raise ValueError(f"RFQ {rfq_id} not found")

    allowed = VALID_TRANSITIONS.get(rfq.status, [])
    if new_status not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition from '{rfq.status}' to '{new_status}'. "
            f"Allowed: {allowed}"
        )

    old_status = rfq.status
    rfq.status = new_status
    rfq.updated_at = _utcnow()

    # Set timestamp for this status
    ts_field = STATUS_TIMESTAMP.get(new_status)
    if ts_field:
        setattr(rfq, ts_field, _utcnow())

    # Apply any extra kwargs (rate_id, odoo_sale_order_id, etc.)
    for key, value in kwargs.items():
        if hasattr(rfq, key):
            setattr(rfq, key, value)

    db.commit()
    db.refresh(rfq)
    _write_audit(db, rfq_id, "status_changed", old_status, new_status)
    return rfq


def get_rfq(db: Session, rfq_id: str) -> RFQWorkflow | None:
    return db.query(RFQWorkflow).filter(RFQWorkflow.id == rfq_id).first()


def list_rfqs(
    db: Session,
    status: str | None = None,
    urgency: str | None = None,
) -> list[RFQWorkflow]:
    q = db.query(RFQWorkflow)
    if status:
        q = q.filter(RFQWorkflow.status == status)
    if urgency:
        q = q.filter(RFQWorkflow.urgency == urgency.upper())
    return q.order_by(RFQWorkflow.created_at.desc()).all()


def get_audit_log(db: Session, rfq_id: str) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .filter(AuditLog.rfq_id == rfq_id)
        .order_by(AuditLog.timestamp)
        .all()
    )


def get_dashboard(db: Session) -> dict:
    all_rfqs = db.query(RFQWorkflow).all()
    by_status: dict[str, int] = {}
    urgent_count = 0
    for rfq in all_rfqs:
        by_status[rfq.status] = by_status.get(rfq.status, 0) + 1
        if rfq.urgency == "URGENT":
            urgent_count += 1
    return {
        "by_status": by_status,
        "total": len(all_rfqs),
        "urgent_count": urgent_count,
    }


def _write_audit(db: Session, rfq_id: str, event: str, old_value: str | None, new_value: str | None):
    entry = AuditLog(rfq_id=rfq_id, event=event, old_value=old_value, new_value=new_value)
    db.add(entry)
    db.commit()
