import asyncio
import os
from typing import Any

from openai import AsyncOpenAI

from production.cache import cached
from production.rate_limiter import with_retry

_MODEL = "text-embedding-3-small"
_BATCH_SIZE = 100

_client: AsyncOpenAI | None = None

def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _client

@with_retry()
async def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    client = _get_client()
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), _BATCH_SIZE):
        batch = texts[i : i + _BATCH_SIZE]
        cleaned = [t.replace("\n", " ").strip() or "." for t in batch]
        response = await client.embeddings.create(model=_MODEL, input=cleaned)
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings

@with_retry()
async def embed_single(text: str) -> list[float]:
    results = await embed_texts([text])
    return results[0]

async def embed_nodes(nodes: list[dict[str, Any]], text_field: str) -> list[dict[str, Any]]:
    texts = [str(n.get(text_field, "")) for n in nodes]
    embeddings = await embed_texts(texts)
    for node, emb in zip(nodes, embeddings):
        node["embedding"] = emb
    return nodes
