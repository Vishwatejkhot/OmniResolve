import hashlib
import hmac
import os

from fastapi import APIRouter, Request, HTTPException

router = APIRouter()

_WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "dev-secret")

def _verify_signature(body: bytes, signature: str) -> bool:
    expected = hmac.new(_WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)

@router.post("/shopify/order-dispute")
async def shopify_dispute_webhook(request: Request) -> dict:
    sig = request.headers.get("X-Shopify-Hmac-Sha256", "")
    body = await request.body()

    import json
    payload = json.loads(body)

    return {
        "received": True,
        "order_id": payload.get("order_id"),
        "dispute_type": payload.get("dispute_type"),
    }

@router.post("/generic")
async def generic_webhook(request: Request) -> dict:
    body = await request.json()
    return {"received": True, "payload_keys": list(body.keys())}
