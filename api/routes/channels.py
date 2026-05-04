from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from channels.email_handler import poll_imap
from channels.document_handler import build_documents_from_attachments

router = APIRouter()

class EmailPollRequest(BaseModel):
    host: str = ""
    user: str = ""
    password: str = ""
    mailbox: str = "INBOX"

@router.post("/email/poll")
async def poll_email(req: EmailPollRequest) -> dict:
    events = list(poll_imap(req.host or None, req.user or None, req.password or None, req.mailbox))
    return {"events_found": len(events), "events": events}

@router.post("/voice/transcribe")
async def transcribe_voice(file: UploadFile = File(...)) -> dict:
    from channels.voice_handler import transcribe_bytes
    audio_bytes = await file.read()
    ext = "." + (file.filename or "audio.wav").rsplit(".", 1)[-1]
    event = transcribe_bytes(audio_bytes, ext)
    return event
