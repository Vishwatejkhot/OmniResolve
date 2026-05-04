import base64
import os
import json
from pathlib import Path

import anthropic

from production.audit_logger import log_evidence
from production.monitoring import trace_node
from production.rate_limiter import with_anthropic_rate_limit, with_retry

_VISION_SYSTEM = """You are an evidence analyst for e-commerce disputes.
Analyse the image and return a JSON object with:
{
  "damage_score": float 0-1 (1 = severe/clear damage),
  "damage_type": string (physical_damage | missing_items | wrong_item | no_damage | unclear),
  "validity_score": float 0-1 (1 = clearly authentic receipt/photo, 0 = suspicious),
  "description": string (plain English, max 100 words)
}
Be objective and evidence-based."""

def _load_image_b64(path_or_url: str) -> tuple[str, str]:
    if path_or_url.startswith("http"):
        import httpx
        resp = httpx.get(path_or_url, timeout=10)
        data = base64.standard_b64encode(resp.content).decode()
        ct = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        return data, ct
    path = Path(path_or_url)
    ext_map = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
    media_type = ext_map.get(path.suffix.lower(), "image/jpeg")
    data = base64.standard_b64encode(path.read_bytes()).decode()
    return data, media_type

@with_retry()
@with_anthropic_rate_limit
async def _analyse_single(doc: dict, client: anthropic.Anthropic, case_id: str) -> dict:
    doc_id = doc.get("id", doc.get("file", "unknown"))
    url = doc.get("url", doc.get("file", ""))

    try:
        img_data, media_type = _load_image_b64(url)
    except Exception as e:
        return {
            "doc_id": doc_id,
            "damage_score": 0.0,
            "validity_score": 0.0,
            "damage_type": "unclear",
            "description": f"Could not load image: {e}",
        }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=_VISION_SYSTEM,
        messages=[{
            "role": "user",
            "content": [{
                "type": "image",
                "source": {"type": "base64", "media_type": media_type, "data": img_data},
            }, {
                "type": "text",
                "text": f"Dispute category: {doc.get('dispute_category', 'unknown')}. Analyse this evidence.",
            }],
        }],
    )

    raw = response.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    result = json.loads(raw[start:end])
    result["doc_id"] = doc_id
    log_evidence(case_id, doc_id, result.get("damage_score", 0.0), result.get("validity_score", 0.0))
    return result

@trace_node("evidence_analyser")
async def evidence_analyser(state: dict) -> dict:
    documents = state.get("documents", [])
    if not documents:
        return {"evidence_scores": {}}

    image_docs = [d for d in documents if d.get("type") in ("photo", "image", "receipt", "screenshot")]
    if not image_docs:
        return {"evidence_scores": {}}

    case_id = state.get("case_id", "unknown")
    category = state.get("dispute_category", "unknown")
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    import asyncio
    tasks = [
        _analyse_single({**doc, "dispute_category": category}, client, case_id)
        for doc in image_docs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    evidence_scores = {}
    for result in results:
        if isinstance(result, Exception):
            continue
        evidence_scores[result["doc_id"]] = {
            "damage_score": result.get("damage_score", 0.0),
            "validity_score": result.get("validity_score", 0.0),
            "damage_type": result.get("damage_type", "unclear"),
            "description": result.get("description", ""),
        }

    return {"evidence_scores": evidence_scores}
