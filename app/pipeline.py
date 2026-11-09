import logging
from email.utils import parseaddr

from app import db
from app.ai.decide import decide
from app.gmail import (
    ESCALATED_LABEL,
    PROCESSED_LABEL,
    Gmail,
    format_thread,
    get_body,
    get_headers,
    has_attachments,
)
from app.guards import skip_reason

logger = logging.getLogger(__name__)
MAX_ATTEMPTS = 3


def handle_message(gmail: Gmail, message_id: str) -> None:
    event = db.start_event(message_id)
    if event is None:
        gmail.add_label(message_id, PROCESSED_LABEL)
        return
    try:
        status, result = process(gmail, message_id)
        gmail.add_label(message_id, PROCESSED_LABEL)
        db.finish_event(event["id"], status, result)
        logger.info("%s %s %s", message_id, status, result)
    except Exception as error:
        db.fail_event(event["id"], str(error))
        if event["attempts"] >= MAX_ATTEMPTS:
            gmail.add_label(message_id, PROCESSED_LABEL)
        raise


def process(gmail: Gmail, message_id: str) -> tuple[str, dict]:
    message = gmail.get_message(message_id)
    headers = get_headers(message)

    reason = skip_reason(message, headers, gmail.address)
    if reason:
        return "skipped", {"reason": reason}

    sender = parseaddr(headers.get("from", ""))[1]
    ticket_id = db.upsert_ticket(message["threadId"], sender, headers.get("subject", ""))
    db.save_message(ticket_id, message_id, "in", sender, get_body(message))

    thread = gmail.get_thread(message["threadId"])
    if gmail.is_escalated(thread):
        # A colleague owns this thread until they remove the needs-human label.
        return "skipped", {"reason": "thread is escalated"}

    decision = decide(format_thread(thread, gmail.address), has_attachments(message))

    sent = gmail.send_reply(message, decision.reply)
    db.save_message(ticket_id, sent["id"], "out", gmail.address, decision.reply)
    if decision.action == "escalate":
        gmail.add_label(message_id, ESCALATED_LABEL)
        db.update_ticket(ticket_id, "escalated", decision.section, decision.proposed_action)
    else:
        db.update_ticket(ticket_id, "answered", decision.section)
    return "processed", decision.model_dump()