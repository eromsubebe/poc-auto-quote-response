"""Storage abstraction for the MVP.

Problem this solves:
- Cloud Run filesystem is ephemeral, so writing emails/attachments to ./poc_data
  will not persist across restarts or across multiple instances.

Approach:
- Always write to /tmp for parsing.
- Persist to GCS when Settings.GCS_BUCKET is configured.
- Otherwise, persist to local disk (dev mode).

Returned values are *references*:
- Local mode: absolute/relative file path
- GCS mode: gs://bucket/prefix/...
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from poc.config import settings


def _get_gcs_client():
    """Create a GCS client lazily.

    We only import google-cloud-storage when GCS is enabled, so local dev
    doesn't require GCP credentials.
    """
    try:
        from google.cloud import storage  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "GCS_BUCKET is set but google-cloud-storage is not installed or failed to import. "
            "Add google-cloud-storage to requirements and redeploy."
        ) from e

    return storage.Client(project=settings.GCP_PROJECT_ID or None)


def write_temp_bytes(filename: str, content: bytes, subdir: str | None = None) -> Path:
    """Write content to a temp file and return its path."""
    base = Path(tempfile.gettempdir())
    if subdir:
        base = base / subdir
        base.mkdir(parents=True, exist_ok=True)
    path = base / filename
    path.write_bytes(content)
    return path


def persist_email_bytes(rfq_id: str, content: bytes) -> tuple[Path, str]:
    """Persist an uploaded .eml.

    Returns:
      (local_temp_path_for_parsing, persisted_reference)
    """
    filename = f"{rfq_id}.eml"
    local_path = write_temp_bytes(filename, content, subdir=f"rfq_emails/{rfq_id}")

    if settings.gcs_enabled:
        ref = _upload_bytes(
            object_path=f"{settings.GCS_PREFIX}/emails/{filename}",
            content=content,
            content_type="message/rfc822",
        )
        return local_path, ref

    # Local dev persistence
    settings.EMAILS_DIR.mkdir(parents=True, exist_ok=True)
    persisted_path = settings.EMAILS_DIR / filename
    persisted_path.write_bytes(content)
    return local_path, str(persisted_path)


def persist_attachment_bytes(rfq_id: str, filename: str, content: bytes) -> tuple[Path, str]:
    """Persist an extracted attachment.

    Returns:
      (local_path_for_parsing, persisted_reference)
    """
    safe_filename = os.path.basename(filename) or "attachment.bin"

    # Local file used for parsing
    local_dir = Path(tempfile.gettempdir()) / "rfq_attachments" / rfq_id
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / safe_filename
    local_path.write_bytes(content)

    if settings.gcs_enabled:
        ref = _upload_bytes(
            object_path=f"{settings.GCS_PREFIX}/attachments/{rfq_id}/{safe_filename}",
            content=content,
            content_type=None,
        )
        return local_path, ref

    # Local dev persistence
    att_dir = settings.ATTACHMENTS_DIR / rfq_id
    att_dir.mkdir(parents=True, exist_ok=True)
    persisted_path = att_dir / safe_filename
    persisted_path.write_bytes(content)
    return persisted_path, str(persisted_path)


def _upload_bytes(object_path: str, content: bytes, content_type: str | None) -> str:
    client = _get_gcs_client()
    bucket = client.bucket(settings.GCS_BUCKET)
    blob = bucket.blob(object_path)
    if content_type:
        blob.content_type = content_type
    blob.upload_from_string(content)
    return f"gs://{settings.GCS_BUCKET}/{object_path}"
