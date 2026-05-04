import random
import uuid
from datetime import datetime, timedelta

from graphrag.neo4j_client import upsert_node, upsert_relationship, run_write
from ingestion.deduplicator import is_duplicate, mark_ingested
from ingestion.embedder import embed_texts

_CATEGORIES = ["fraud", "damage", "non_delivery", "other"]
_CHANNELS = ["web", "mobile", "phone", "email"]
_RESOLUTIONS = ["refund", "replace", "reject", "escalate"]
_PRODUCT_CATEGORIES = ["electronics", "clothing", "furniture", "toys", "books", "food"]

def _random_date(days_back: int = 365) -> datetime:
    return datetime.utcnow() - timedelta(days=random.randint(0, days_back))

def _generate_synthetic_case(_index: int) -> dict:
    customer_id = f"cust_{random.randint(1, 100):04d}"
    seller_id = f"seller_{random.randint(1, 20):03d}"
    product_sku = f"SKU-{random.randint(1000, 9999)}"
    order_id = f"ord_{uuid.uuid4().hex[:8]}"
    dispute_id = f"disp_{uuid.uuid4().hex[:8]}"
    category = random.choice(_CATEGORIES)
    resolution = random.choice(_RESOLUTIONS)

    return {
        "customer": {
            "id": customer_id,
            "name": f"Customer {customer_id}",
            "email": f"{customer_id}@example.com",
            "dispute_count": random.randint(0, 5),
            "fraud_risk_score": round(random.uniform(0.0, 0.4), 3),
        },
        "seller": {
            "id": seller_id,
            "name": f"Seller {seller_id}",
            "dispute_rate": round(random.uniform(0.01, 0.15), 3),
            "refund_rate": round(random.uniform(0.02, 0.20), 3),
            "fraud_signals": random.randint(0, 3),
        },
        "product": {
            "sku": product_sku,
            "name": f"Product {product_sku}",
            "category": random.choice(_PRODUCT_CATEGORIES),
            "defect_rate": round(random.uniform(0.001, 0.05), 4),
            "return_rate": round(random.uniform(0.01, 0.12), 4),
        },
        "order": {
            "id": order_id,
            "date": _random_date(400).isoformat(),
            "total_value": round(random.uniform(5.0, 500.0), 2),
            "status": random.choice(["delivered", "in_transit", "cancelled"]),
            "channel": random.choice(_CHANNELS),
        },
        "dispute": {
            "id": dispute_id,
            "category": category,
            "channel": random.choice(_CHANNELS),
            "status": "resolved",
            "resolution": resolution,
            "confidence": round(random.uniform(0.6, 0.99), 3),
            "text": (
                f"Customer raised a {category} dispute for order {order_id}. "
                f"Product {product_sku} was reported as having issues. "
                f"Case resolved with {resolution}."
            ),
        },
    }

async def ingest_single_case(case: dict) -> str:
    dispute_id = case["dispute"]["id"]
    if is_duplicate({"dispute_id": dispute_id}):
        return dispute_id

    dispute_text = case["dispute"].get("text", case["dispute"]["category"])
    embeddings = await embed_texts([dispute_text])
    case["dispute"]["embedding"] = embeddings[0]
    case["dispute"].pop("text", None)

    await upsert_node("Customer", "id", case["customer"])
    await upsert_node("Seller", "id", case["seller"])
    await upsert_node("Product", "sku", case["product"])
    await upsert_node("Order", "id", case["order"])
    await upsert_node("Dispute", "id", case["dispute"])

    await upsert_relationship("Customer", "id", case["customer"]["id"], "PLACED", "Order", "id", case["order"]["id"])
    await upsert_relationship("Order", "id", case["order"]["id"], "CONTAINS", "Product", "sku", case["product"]["sku"])
    await upsert_relationship("Product", "sku", case["product"]["sku"], "SOLD_BY", "Seller", "id", case["seller"]["id"])
    await upsert_relationship("Customer", "id", case["customer"]["id"], "RAISED", "Dispute", "id", dispute_id)
    await upsert_relationship("Dispute", "id", dispute_id, "CONCERNS", "Order", "id", case["order"]["id"])

    mark_ingested({"dispute_id": dispute_id})
    return dispute_id

async def compute_similarity_edges(top_k: int = 5) -> int:
    cypher = f"""
        MATCH (d1:Dispute), (d2:Dispute)
        WHERE d1.id <> d2.id AND d1.embedding IS NOT NULL AND d2.embedding IS NOT NULL
        WITH d1, d2,
             gds.similarity.cosine(d1.embedding, d2.embedding) AS score
        WHERE score > 0.75
        WITH d1, d2, score ORDER BY score DESC
        WITH d1, collect({{d2: d2, score: score}})[0..{top_k}] AS neighbors
        UNWIND neighbors AS n
        MERGE (d1)-[r:SIMILAR_TO]->(n.d2)
        SET r.score = n.score
        RETURN count(r) AS edges_created
    """
    await run_write(cypher)
    return 0

async def seed_graph(n: int = 500) -> int:
    count = 0
    for i in range(n):
        case = _generate_synthetic_case(i)
        await ingest_single_case(case)
        count += 1
        if (i + 1) % 50 == 0:
            print(f"Ingested {i + 1}/{n} cases...")
    return count

async def load_from_json(disputes_path: str = "data/disputes.json") -> int:
    import json
    from pathlib import Path
    path = Path(disputes_path)
    if not path.exists():
        print(f"  {path} not found — run: python scripts/generate_data.py")
        return 0
    with open(path, encoding="utf-8") as f:
        records = json.load(f)

    count = 0
    for record in records:
        disp = record["dispute"]
        case = {
            "customer": {"id": record["customer_id"], "name": record["customer_id"],
                         "email": f"{record['customer_id']}@example.com",
                         "dispute_count": 0, "fraud_risk_score": 0.0},
            "seller": {"id": record["seller_id"], "name": record["seller_id"],
                       "dispute_rate": 0.0, "refund_rate": 0.0, "fraud_signals": 0},
            "product": {"sku": record["product_sku"], "name": record["product_sku"],
                        "category": "general", "defect_rate": 0.0, "return_rate": 0.0},
            "order": record["order"],
            "dispute": {
                **disp,
                "text": disp.get("description", disp.get("category", "")),
            },
        }
        await ingest_single_case(case)
        count += 1
        if count % 50 == 0:
            print(f"  Loaded {count}/{len(records)} from JSON...")
    return count
