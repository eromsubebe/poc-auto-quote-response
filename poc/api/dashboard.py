from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from poc.database import get_db
from poc.schemas import DashboardOverview
from poc.services import workflow_service
from poc.services.sla_monitor import get_sla_alerts, get_sla_statistics

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
def dashboard_overview(db: Session = Depends(get_db)):
    return workflow_service.get_dashboard(db)


@router.get("/sla-alerts")
def sla_alerts(
    include_breached: bool = Query(True, description="Include already-breached RFQs"),
    approaching_hours: int = Query(2, description="Hours before deadline to flag as approaching"),
    db: Session = Depends(get_db),
):
    """Get SLA alerts for the dashboard.

    Returns RFQs categorized by SLA status:
    - breached: RFQs that have exceeded their SLA deadline
    - approaching: RFQs approaching deadline (within approaching_hours)
    - on_track_count: Count of RFQs with plenty of time remaining
    """
    return get_sla_alerts(db, include_breached=include_breached, approaching_hours=approaching_hours)


@router.get("/sla-statistics")
def sla_statistics(
    days: int = Query(7, description="Number of days to analyze"),
    db: Session = Depends(get_db),
):
    """Get SLA performance statistics.

    Returns metrics like:
    - Total completed RFQs
    - On-time vs breached counts
    - On-time percentage
    - Average response time
    """
    return get_sla_statistics(db, days=days)
