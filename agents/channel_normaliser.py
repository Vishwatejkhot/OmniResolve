import re
from typing import Any

from production.monitoring import trace_node

_PII_PATTERNS = [
    (re.compile(r"\b[A-Z]{2}\d{6}[A-Z]\b"), "[NI_NUMBER]"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD_NUMBER]"),
    (re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"), "[PHONE]"),
]

def _strip_pii(text: str) -> str:
    for pattern, replacement in _PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

def _normalise_event(raw: dict[str, Any]) -> dict[str, Any]:
    channel = raw.get("channel", "unknown")
    content = raw.get("content", raw.get("text", raw.get("body", "")))
    if isinstance(content, str):
        content = _strip_pii(content)
    return {
        "channel": channel,
        "content": content,
        "sender": raw.get("sender", raw.get("from", raw.get("email", ""))),
        "timestamp": raw.get("timestamp", raw.get("date", "")),
        "attachments": raw.get("attachments", []),
        "raw_channel_id": raw.get("id", raw.get("message_id", "")),
    }

@trace_node("channel_normaliser")
async def channel_normaliser(state: dict) -> dict:
    raw_events: list[dict] = state.get("_raw_events", [])

    normalised = [_normalise_event(e) for e in raw_events]

    updates: dict[str, Any] = {"channel_history": normalised}

    if not state.get("order_id") and normalised:
        latest = normalised[-1]
        content = latest.get("content", "")
        order_match = re.search(r"\bord[_-]?([A-Za-z0-9]{6,12})\b", content, re.IGNORECASE)
        if order_match:
            updates["order_id"] = f"ord_{order_match.group(1)}"

    return updates
