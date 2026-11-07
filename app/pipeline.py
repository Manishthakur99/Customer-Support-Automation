import logging

from app.gmail import PROCESSED_LABEL, Gmail, get_headers

logger = logging.getLogger(__name__)


def handle_message(gmail: Gmail, message_id: str) -> None:
    message = gmail.get_message(message_id)
    headers = get_headers(message)
    logger.info("New email from %s: %s", headers.get("from"), headers.get("subject"))
    gmail.add_label(message_id, PROCESSED_LABEL)