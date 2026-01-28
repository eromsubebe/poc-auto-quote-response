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

    # GCP / Vertex AI configuration
    GCP_PROJECT_ID: str = ""
    GCP_REGION: str = "us-central1"
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_EXTRACTION_ENABLED: bool = True

    # SLA configuration
    SLA_TARGET_HOURS_STANDARD: int = 24
    SLA_TARGET_HOURS_URGENT: int = 4
    SLA_CHECK_INTERVAL_MINUTES: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def imap_enabled(self) -> bool:
        return bool(self.IMAP_HOST and self.IMAP_USER and self.IMAP_PASSWORD)

    @property
    def gemini_enabled(self) -> bool:
        """Check if Gemini extraction is enabled and configured."""
        return bool(self.GEMINI_EXTRACTION_ENABLED and self.GCP_PROJECT_ID)


settings = Settings()
