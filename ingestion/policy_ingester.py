import hashlib
from datetime import datetime

from graphrag.neo4j_client import upsert_node, upsert_relationship
from ingestion.deduplicator import is_duplicate, mark_ingested
from ingestion.embedder import embed_texts

CONSUMER_RIGHTS_ACT_CLAUSES = [
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 9",
        "text": (
            "Every contract to supply goods is to be treated as including a term that "
            "the quality of the goods is satisfactory. Goods are of satisfactory quality "
            "if they meet the standard that a reasonable person would consider satisfactory, "
            "taking account of description, price, and all other relevant circumstances."
        ),
    },
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 10",
        "text": (
            "Where the contract is to supply goods, the goods must be fit for any particular "
            "purpose made known by the consumer to the trader, before the contract is made, "
            "expressly or by implication."
        ),
    },
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 11",
        "text": (
            "Where goods are sold by description, the goods must match the description. "
            "Where the sale is by sample as well as by description, it is not sufficient "
            "that the bulk corresponds with the sample if the goods do not also correspond "
            "with the description."
        ),
    },
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 19",
        "text": (
            "If goods do not conform to the contract at the time of delivery, the consumer "
            "has the right to repair or replacement. If repair or replacement is not possible "
            "or is disproportionate, the consumer has the right to a reduction in price or "
            "the final right to reject."
        ),
    },
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 20",
        "text": (
            "A consumer who has the right to reject goods may reject the goods within 30 days "
            "of delivery. After the 30-day period, the consumer loses the short-term right to "
            "reject but retains rights to repair, replacement, or price reduction."
        ),
    },
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 23",
        "text": (
            "The trader must repair or replace goods within a reasonable time and without "
            "causing significant inconvenience to the consumer. The consumer must give the "
            "trader goods that need to be repaired or replaced."
        ),
    },
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 28",
        "text": (
            "Unless otherwise agreed, the trader must deliver the goods without undue delay "
            "and in any event not more than 30 days after the day the contract is entered into. "
            "If delivery is not made within this period the consumer may treat the contract as "
            "at an end."
        ),
    },
    {
        "act": "Consumer Rights Act 2015",
        "section": "Section 59",
        "text": (
            "A trader must perform the service with reasonable care and skill. Any information "
            "provided by the trader about the service, before the contract is entered into, "
            "is to be treated as a term of the contract."
        ),
    },
]

async def ingest_legal_clauses() -> int:
    texts = [c["text"] for c in CONSUMER_RIGHTS_ACT_CLAUSES]
    embeddings = await embed_texts(texts)
    count = 0
    for clause, emb in zip(CONSUMER_RIGHTS_ACT_CLAUSES, embeddings):
        if is_duplicate(clause):
            continue
        node_id = hashlib.md5(f"{clause['act']}:{clause['section']}".encode()).hexdigest()
        await upsert_node("LegalClause", "id", {
            "id": node_id,
            "act": clause["act"],
            "section": clause["section"],
            "text": clause["text"],
            "embedding": emb,
        })
        mark_ingested(clause)
        count += 1
    return count

async def ingest_policy(
    policy_id: str,
    source: str,
    clause: str,
    text: str,
    seller_id: str | None = None,
    version_date: datetime | None = None,
) -> None:
    if is_duplicate({"id": policy_id, "text": text}):
        return
    embeddings = await embed_texts([text])
    await upsert_node("Policy", "id", {
        "id": policy_id,
        "source": source,
        "clause": clause,
        "text": text,
        "embedding": embeddings[0],
        "version_date": (version_date or datetime.utcnow()).isoformat(),
    })
    if seller_id:
        await upsert_relationship("Seller", "id", seller_id, "SUBJECT_TO", "Policy", "id", policy_id)
    mark_ingested({"id": policy_id, "text": text})
