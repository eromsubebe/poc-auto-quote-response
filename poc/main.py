import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from poc.config import settings
from poc.database import create_tables

logger = logging.getLogger("poc")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting POC RFQ Automation API")
    create_tables()
    settings.EMAILS_DIR.mkdir(parents=True, exist_ok=True)
    settings.ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    scheduler = None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from poc.database import SessionLocal

        scheduler = BackgroundScheduler()

        # SLA monitoring job - runs every N minutes
        def _sla_check_job():
            from poc.services.sla_monitor import run_sla_check
            db = SessionLocal()
            try:
                run_sla_check(db)
            finally:
                db.close()

        scheduler.add_job(
            _sla_check_job,
            "interval",
            minutes=settings.SLA_CHECK_INTERVAL_MINUTES,
            id="sla_monitor",
        )
        logger.info(f"SLA monitoring enabled (every {settings.SLA_CHECK_INTERVAL_MINUTES} minutes)")

        # Optional IMAP scheduler
        if settings.imap_enabled:
            from poc.services.imap_poller import poll_imap
            from poc.api.rfqs import _run_pipeline

            def _imap_job():
                def callback(eml_path: str):
                    db = SessionLocal()
                    try:
                        _run_pipeline(db, eml_path)
                    finally:
                        db.close()
                poll_imap(callback)

            scheduler.add_job(
                _imap_job,
                "interval",
                seconds=settings.IMAP_POLL_INTERVAL_SECONDS,
                id="imap_poller",
            )
            logger.info(f"IMAP polling enabled (every {settings.IMAP_POLL_INTERVAL_SECONDS}s)")

        scheduler.start()

    except ImportError:
        logger.warning("apscheduler not installed — background jobs disabled")

    yield

    # Shutdown
    if scheduler:
        scheduler.shutdown(wait=False)
    logger.info("POC RFQ Automation API shut down")


app = FastAPI(
    title="Creseada RFQ Automation POC",
    description="Hybrid RFQ automation: email parse → rate lookup → mock Odoo quote → team lead review",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
from poc.api import dashboard, export, rates, rfqs  # noqa: E402

app.include_router(rfqs.router)
app.include_router(rates.router)
app.include_router(dashboard.router)
app.include_router(export.router, prefix="/api/rfqs", tags=["export"])


@app.get("/health")
def health():
    return {"status": "ok"}
