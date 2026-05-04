import os
import json

import anthropic
from pydantic import BaseModel

from production.cache import cached
from production.monitoring import trace_node
from production.rate_limiter import with_anthropic_rate_limit, with_retry

class ClassificationResult(BaseModel):
    category: str
    confidence: float
    reasoning: str

_SYSTEM = """You are a dispute classification specialist for an e-commerce platform.
Classify the customer's dispute into exactly one of these categories:
- fraud: unauthorised transaction, identity theft, account compromise
- damage: item arrived damaged, defective, or not as described
- non_delivery: item not received, tracking shows lost, significant delay
- other: billing error, return/refund issue, or anything not fitting above

Respond in JSON: {"category": "...", "confidence": 0.0-1.0, "reasoning": "..."}"""

@cached()
@with_retry()
@with_anthropic_rate_limit
@trace_node("dispute_classifier")
async def dispute_classifier(state: dict) -> dict:
    history = state.get("channel_history", [])
    conversation = "\n".join(
        f"[{e.get('channel', '?').upper()}] {e.get('content', '')}"
        for e in history[-5:]
    )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=_SYSTEM,
        messages=[{"role": "user", "content": conversation}],
    )

    raw = response.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    parsed = json.loads(raw[start:end])
    result = ClassificationResult(**parsed)

    return {
        "dispute_category": result.category,
        "confidence_score": result.confidence,
    }
