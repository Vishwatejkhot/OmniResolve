import email
import imaplib
import os
import re
from datetime import datetime, timezone
from email.header import decode_header
from typing import Generator

def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    result = []
    for part, charset in parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return " ".join(result)

def _extract_text_body(msg: email.message.Message) -> str:
    body_parts = []
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(payload.decode(msg.get_content_charset() or "utf-8", errors="replace"))
    return "\n".join(body_parts).strip()

def _extract_attachments(msg: email.message.Message) -> list[dict]:
    attachments = []
    for part in msg.walk():
        if part.get_content_disposition() == "attachment":
            filename = part.get_filename() or "attachment"
            attachments.append({
                "filename": filename,
                "content_type": part.get_content_type(),
                "data": part.get_payload(decode=True),
            })
    return attachments

def parse_email_message(raw_bytes: bytes) -> dict:
    msg = email.message_from_bytes(raw_bytes)
    sender = _decode_header_value(msg.get("From", ""))
    subject = _decode_header_value(msg.get("Subject", ""))
    date_str = msg.get("Date", "")
    body = _extract_text_body(msg)
    attachments = _extract_attachments(msg)

    order_id = ""
    for text in (subject, body):
        m = re.search(r"\bord[_-]?([A-Za-z0-9]{6,12})\b", text, re.IGNORECASE)
        if m:
            order_id = f"ord_{m.group(1)}"
            break

    return {
        "channel": "email",
        "content": f"Subject: {subject}\n\n{body}",
        "sender": sender,
        "timestamp": date_str or datetime.now(timezone.utc).isoformat(),
        "attachments": [
            {"filename": a["filename"], "type": a["content_type"]}
            for a in attachments
        ],
        "raw_channel_id": msg.get("Message-ID", ""),
        "order_id": order_id,
        "_raw_attachments": attachments,
    }

def poll_imap(
    host: str | None = None,
    user: str | None = None,
    password: str | None = None,
    mailbox: str = "INBOX",
) -> Generator[dict, None, None]:
    host = host or os.environ.get("IMAP_HOST", "")
    user = user or os.environ.get("IMAP_USER", "")
    password = password or os.environ.get("IMAP_PASSWORD", "")

    if not all([host, user, password]):
        return

    mail = imaplib.IMAP4_SSL(host)
    mail.login(user, password)
    mail.select(mailbox)
    _, data = mail.search(None, "UNSEEN")
    ids = data[0].split()
    for msg_id in ids:
        _, raw_data = mail.fetch(msg_id, "(RFC822)")
        raw_bytes = raw_data[0][1]
        yield parse_email_message(raw_bytes)
        mail.store(msg_id, "+FLAGS", "\\Seen")
    mail.close()
    mail.logout()
