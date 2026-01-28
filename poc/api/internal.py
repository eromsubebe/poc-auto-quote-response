"""Internal endpoints (for schedulers, ops automation).

These endpoints are NOT meant for end-users.
For MVP we protect them with a shared header token.

Recommended Cloud Run setup:
- Cloud Scheduler runs every 5 minutes
- POST https://<backend-url>/api/internal/sla/run
- Header: X-Cron-Token: <INTERNAL_CRON_TOKEN>

Later, replace header auth with Scheduler OIDC + IAM.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from poc.config import settings
from poc.database import get_db
from poc.services.sla_monitor import run_sla_check

router = APIRouter(prefix="/api/internal", tags=["internal"])


def _require_cron_token(x_cron_token: str | None = Header(default=None, alias="X-Cron-Token")) -> None:
    """Very small MVP guardrail.

    - If INTERNAL_CRON_TOKEN is not configured, the endpoint is disabled.
    - If configured, caller must provide matching X-Cron-Token header.

    This avoids accidentally exposing operational endpoints publicly.
    """
    if not settings.INTERNAL_CRON_TOKEN:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_cron_token or x_cron_token != settings.INTERNAL_CRON_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/sla/run")
def trigger_sla_check(
    _: None = Depends(_require_cron_token),
    db: Session = Depends(get_db),
):
    """Run SLA checks for open RFQs.

    Expected to be called by Cloud Scheduler.
    """
    return run_sla_check(db)
