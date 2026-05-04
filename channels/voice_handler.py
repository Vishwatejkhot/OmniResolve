import io
import os
import tempfile
from pathlib import Path

import whisper

_model: whisper.Whisper | None = None
_MODEL_SIZE = os.getenv("WHISPER_MODEL", "large-v3")

def _get_model() -> whisper.Whisper:
    global _model
    if _model is None:
        _model = whisper.load_model(_MODEL_SIZE)
    return _model

def transcribe_file(audio_path: str | Path) -> dict:
    model = _get_model()
    result = model.transcribe(str(audio_path), language="en", fp16=False)
    text = result.get("text", "").strip()
    return {
        "channel": "voice",
        "content": text,
        "sender": "",
        "timestamp": "",
        "attachments": [],
        "raw_channel_id": str(audio_path),
        "segments": result.get("segments", []),
    }

def transcribe_bytes(audio_bytes: bytes, extension: str = ".wav") -> dict:
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name
    try:
        return transcribe_file(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

async def handle_voice_upload(audio_bytes: bytes, sender_email: str = "") -> dict:
    event = transcribe_bytes(audio_bytes)
    event["sender"] = sender_email
    return event
