"""SLA monitoring service for tracking RFQ response deadlines.

This module provides background monitoring of SLA targets and marks
RFQs as breached when deadlines are exceeded.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from poc.config import settings
from poc.db_models import AuditLog, RFQWorkflow

logger = logging.getLogger(__name__)


# Terminal states where SLA no longer applies
TERMINAL_STATUSES = {"sent", "cancelled", "rejected"}

# Statuses that are considered "open" for SLA tracking
OPEN_STATUSES = {"received", "parsing", "rates_lookup", "rates_pending", "rates_found", "quote_draft", "quote_review"}


def calculate_sla_deadline(urgency: str, received_at: datetime) -> tuple[int, datetime]:
    """Calculate SLA deadline based on urgency level.

    Args:
        urgency: "URGENT" or "STANDARD"
        received_at: When the RFQ was received

    Returns:
        Tuple of (target_hours, deadline_datetime)
    """
    if urgency == "URGENT":
        target_hours = settings.SLA_TARGET_HOURS_URGENT
    else:
        target_hours = settings.SLA_TARGET_HOURS_STANDARD

    # Ensure received_at is timezone-aware
    if received_at.tzinfo is None:
        received_at = received_at.replace(tzinfo=timezone.utc)

    deadline = received_at + timedelta(hours=target_hours)
    return target_hours, deadline


def set_sla_deadline(db: Session, rfq: RFQWorkflow) -> None:
    """Set the SLA deadline for an RFQ based on its urgency.

    Should be called when an RFQ is created or when urgency changes.

    Args:
        db: Database session
        rfq: The RFQ workflow record
    """
    received = rfq.received_at or rfq.created_at
    if not received:
        received = datetime.now(timezone.utc)

    target_hours, deadline = calculate_sla_deadline(rfq.urgency, received)

    rfq.sla_target_hours = target_hours
    rfq.sla_deadline_at = deadline
    rfq.sla_breached = False
    rfq.sla_breached_at = None

    db.commit()
    logger.debug(f"Set SLA for RFQ {rfq.id}: {target_hours}h deadline at {deadline}")


def check_sla_breach(db: Session, rfq: RFQWorkflow) -> bool:
    """Check if an RFQ has breached its SLA deadline.

    Args:
        db: Database session
        rfq: The RFQ workflow record

    Returns:
        True if newly breached, False otherwise
    """
    # Skip if already breached or in terminal state
    if rfq.sla_breached or rfq.status in TERMINAL_STATUSES:
        return False

    # Skip if no deadline set
    if not rfq.sla_deadline_at:
        return False

    now = datetime.now(timezone.utc)
    deadline = rfq.sla_deadline_at
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)

    if now > deadline:
        rfq.sla_breached = True
        rfq.sla_breached_at = now

        # Log the breach
        audit = AuditLog(
            rfq_id=rfq.id,
            event="sla_breached",
            old_value=None,
            new_value=f"Deadline was {deadline.isoformat()}, breached at {now.isoformat()}"
        )
        db.add(audit)
        db.commit()

        logger.warning(f"RFQ {rfq.id} breached SLA (deadline: {deadline}, status: {rfq.status})")
        return True

    return False


def run_sla_check(db: Session) -> dict:
    """Run SLA check on all open RFQs.

    This is the main function to be called by the background scheduler.

    Args:
        db: Database session

    Returns:
        Summary dict with check results
    """
    open_rfqs = db.query(RFQWorkflow).filter(
        RFQWorkflow.status.in_(OPEN_STATUSES),
        RFQWorkflow.sla_breached == False,  # noqa: E712
        RFQWorkflow.sla_deadline_at.isnot(None)
    ).all()

    newly_breached = 0
    checked = 0

    for rfq in open_rfqs:
        checked += 1
        if check_sla_breach(db, rfq):
            newly_breached += 1

    logger.info(f"SLA check completed: {checked} RFQs checked, {newly_breached} newly breached")

    return {
        "checked": checked,
        "newly_breached": newly_breached,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_sla_alerts(db: Session, include_breached: bool = True, approaching_hours: int = 2) -> dict:
    """Get SLA alerts for dashboard display.

    Args:
        db: Database session
        include_breached: Include already-breached RFQs
        approaching_hours: Hours before deadline to consider "approaching"

    Returns:
        Dict with categorized SLA alerts
    """
    now = datetime.now(timezone.utc)
    approaching_threshold = now + timedelta(hours=approaching_hours)

    # Get all open RFQs with SLA deadlines
    open_rfqs = db.query(RFQWorkflow).filter(
        RFQWorkflow.status.in_(OPEN_STATUSES),
        RFQWorkflow.sla_deadline_at.isnot(None)
    ).all()

    breached = []
    approaching = []
    on_track = []

    for rfq in open_rfqs:
        deadline = rfq.sla_deadline_at
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        time_remaining = deadline - now
        hours_remaining = time_remaining.total_seconds() / 3600

        alert_data = {
            "rfq_id": rfq.id,
            "rfq_reference": rfq.rfq_reference,
            "customer_name": rfq.customer_name,
            "subject": rfq.subject,
            "status": rfq.status,
            "urgency": rfq.urgency,
            "sla_deadline_at": deadline.isoformat(),
            "hours_remaining": round(hours_remaining, 1),
            "sla_target_hours": rfq.sla_target_hours,
            "assigned_agent": rfq.assigned_agent,
        }

        if rfq.sla_breached or hours_remaining < 0:
            alert_data["sla_breached_at"] = rfq.sla_breached_at.isoformat() if rfq.sla_breached_at else now.isoformat()
            breached.append(alert_data)
        elif deadline <= approaching_threshold:
            approaching.append(alert_data)
        else:
            on_track.append(alert_data)

    # Sort by urgency (breached by how long ago, approaching by deadline)
    breached.sort(key=lambda x: x["hours_remaining"])
    approaching.sort(key=lambda x: x["hours_remaining"])

    result = {
        "summary": {
            "breached_count": len(breached),
            "approaching_count": len(approaching),
            "on_track_count": len(on_track),
            "total_open": len(open_rfqs),
        },
        "approaching": approaching,
        "on_track_count": len(on_track),
    }

    if include_breached:
        result["breached"] = breached

    return result


def get_sla_statistics(db: Session, days: int = 7) -> dict:
    """Get SLA performance statistics.

    Args:
        db: Database session
        days: Number of days to look back

    Returns:
        Dict with SLA performance metrics
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Get completed RFQs in the period
    completed = db.query(RFQWorkflow).filter(
        RFQWorkflow.status == "sent",
        RFQWorkflow.quote_sent_at >= cutoff
    ).all()

    total_completed = len(completed)
    breached_count = sum(1 for rfq in completed if rfq.sla_breached)
    on_time_count = total_completed - breached_count

    # Calculate average response time
    response_times = []
    for rfq in completed:
        if rfq.received_at and rfq.quote_sent_at:
            delta = rfq.quote_sent_at - rfq.received_at
            response_times.append(delta.total_seconds() / 3600)

    avg_response_hours = sum(response_times) / len(response_times) if response_times else None

    return {
        "period_days": days,
        "total_completed": total_completed,
        "on_time_count": on_time_count,
        "breached_count": breached_count,
        "on_time_percentage": round(on_time_count / total_completed * 100, 1) if total_completed > 0 else None,
        "avg_response_hours": round(avg_response_hours, 1) if avg_response_hours else None,
    }
