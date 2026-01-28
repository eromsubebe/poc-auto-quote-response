import email
import imaplib
import logging
import uuid
from pathlib import Path

from poc.config import settings

logger = logging.getLogger(__name__)


def poll_imap(pipeline_callback):
    """Poll IMAP mailbox for unseen messages and feed them into the pipeline.

    Args:
        pipeline_callback: Callable(eml_path: str) that runs the RFQ upload pipeline.
    """
    if not settings.imap_enabled:
        return

    try:
        conn = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
        conn.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
        conn.select(settings.IMAP_FOLDER)

        _status, message_ids = conn.search(None, "UNSEEN")
        if not message_ids or not message_ids[0]:
            conn.logout()
            return

        for msg_id in message_ids[0].split():
            try:
                _status, msg_data = conn.fetch(msg_id, "(RFC822)")
                raw_email = msg_data[0][1]

                # Save to disk
                eml_filename = f"{uuid.uuid4()}.eml"
                eml_path = settings.EMAILS_DIR / eml_filename
                eml_path.parent.mkdir(parents=True, exist_ok=True)
                eml_path.write_bytes(raw_email)

                # Feed into pipeline
                pipeline_callback(str(eml_path))

                # Mark as seen
                conn.store(msg_id, "+FLAGS", "\\Seen")
                logger.info(f"Processed email: {eml_filename}")

            except Exception:
                logger.exception(f"Failed to process message {msg_id}")

        conn.logout()

    except Exception:
        logger.exception("IMAP polling failed")
