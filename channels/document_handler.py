import hashlib
import mimetypes
import os
import uuid
from pathlib import Path

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_DOC_TYPES = {"application/pdf", "text/plain"}

def save_upload(file_bytes: bytes, filename: str) -> dict:
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    ext = Path(filename).suffix.lower()
    safe_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / safe_name
    dest.write_bytes(file_bytes)

    doc_type = _classify_doc_type(content_type, ext)

    return {
        "id": safe_name,
        "file": str(dest),
        "url": str(dest),
        "type": doc_type,
        "filename": filename,
        "content_type": content_type,
        "size_bytes": len(file_bytes),
        "md5": hashlib.md5(file_bytes).hexdigest(),
        "processed": False,
    }

def _classify_doc_type(content_type: str, ext: str) -> str:
    if content_type in _IMAGE_TYPES or ext in (".jpg", ".jpeg", ".png", ".webp"):
        return "photo"
    if ext in (".pdf",):
        return "receipt"
    if ext in (".txt", ".csv"):
        return "document"
    return "other"

async def extract_text_from_pdf(file_path: str | Path) -> str:
    try:
        import pypdf
        reader = pypdf.PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""

def build_documents_from_attachments(attachments: list[dict]) -> list[dict]:
    docs = []
    for att in attachments:
        raw = att.get("data", b"")
        if not raw:
            continue
        doc = save_upload(raw, att.get("filename", "attachment"))
        docs.append(doc)
    return docs
