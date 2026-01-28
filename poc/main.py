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

    # Local dev convenience only. On Cloud Run, storage should be GCS.
    if not settings.gcs_enabled:
        settings.EMAILS_DIR.mkdir(parents=True, exist_ok=True)
        settings.ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    # NOTE: Do NOT run background schedulers inside the API process on Cloud Run.
    # Use Cloud Scheduler → HTTP to trigger /api/internal/sla/run instead.

    yield
    logger.info("POC RFQ Automation API shut down")


app = FastAPI(
    title="Creseada RFQ Automation POC",
    description="Hybrid RFQ automation: email parse → rate lookup → mock Odoo quote → team lead review",
    version="0.1.0",
    lifespan=lifespan,
)

# Include routers
from poc.api import dashboard, export, internal, rates, rfqs  # noqa: E402

app.include_router(rfqs.router)
app.include_router(rates.router)
app.include_router(dashboard.router)
app.include_router(export.router, prefix="/api/rfqs", tags=["export"])
app.include_router(internal.router)


@app.get("/health")
def health():
    return {"status": "ok"}
