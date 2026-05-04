from datetime import datetime, timezone
from typing import Any

def normalise_chat_message(payload: dict[str, Any]) -> dict:
    return {
        "channel": "chat",
        "content": payload.get("message", ""),
        "sender": payload.get("email", payload.get("customer_id", "")),
        "timestamp": payload.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "attachments": payload.get("attachments", []),
        "raw_channel_id": payload.get("message_id", ""),
        "session_id": payload.get("session_id", ""),
        "order_id": payload.get("order_id", ""),
    }

def extract_state_hints(payload: dict) -> dict:
    hints = {}
    if payload.get("session_id"):
        hints["session_id"] = payload["session_id"]
    if payload.get("order_id"):
        hints["order_id"] = payload["order_id"]
    if payload.get("customer_id"):
        hints["customer_id"] = payload["customer_id"]
    return hints
