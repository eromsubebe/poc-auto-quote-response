from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite:///./poc_data/rfq.db"

    # IMAP (all optional — if IMAP_HOST is empty, polling is disabled)
    IMAP_HOST: str = ""
    IMAP_PORT: int = 993
    IMAP_USER: str = ""
    IMAP_PASSWORD: str = ""
    IMAP_FOLDER: str = "INBOX"
    IMAP_POLL_INTERVAL_SECONDS: int = 60

    # Storage directories
    EMAILS_DIR: Path = Path("./poc_data/emails")
    ATTACHMENTS_DIR: Path = Path("./poc_data/attachments")

    # Optional: persistent storage in GCS (recommended for Cloud Run)
    # If set, uploaded .eml files and extracted attachments are stored in this bucket.
    # The API still writes temporary files to /tmp for parsing.
    GCS_BUCKET: str = ""
    GCS_PREFIX: str = "rfq-poc"  # folder prefix inside the bucket

    # GCP / Vertex AI configuration
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    # Default OFF for MVP; enable explicitly via env var when you're ready.
    GEMINI_EXTRACTION_ENABLED: bool = False

    # Internal endpoints (e.g., Cloud Scheduler calling SLA checks)
    INTERNAL_CRON_TOKEN: str = ""

    # SLA configuration
    # Align with the business expectation: same-day responses.
    # Standard: 4–5 hours, Urgent: shorter (tune during discovery/pilot).
    SLA_TARGET_HOURS_STANDARD: int = 5
    SLA_TARGET_HOURS_URGENT: int = 2
    SLA_CHECK_INTERVAL_MINUTES: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def imap_enabled(self) -> bool:
        return bool(self.IMAP_HOST and self.IMAP_USER and self.IMAP_PASSWORD)

    @property
    def gemini_enabled(self) -> bool:
        """Check if Gemini extraction is enabled and configured."""
        return bool(self.GEMINI_EXTRACTION_ENABLED and self.GCP_PROJECT_ID)

    @property
    def gcs_enabled(self) -> bool:
        return bool(self.GCS_BUCKET)


settings = Settings()
