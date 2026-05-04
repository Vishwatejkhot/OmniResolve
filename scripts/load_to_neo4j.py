import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

DATA_DIR = Path(__file__).parent.parent / "data"

async def _apply_schema():
    from graphrag.neo4j_client import apply_schema
    print("Applying Neo4j schema and vector indexes...")
    await apply_schema()
    print("  Schema OK")

async def _load_customers(customers: list[dict]) -> int:
    from graphrag.neo4j_client import upsert_node
    print(f"Loading {len(customers)} customers...")
    for c in customers:
        await upsert_node("Customer", "id", {
            "id": c["id"],
            "name": c["name"],
            "email": c["email"],
            "phone": c.get("phone", ""),
            "city": c.get("city", ""),
            "dispute_count": c.get("dispute_count", 0),
            "fraud_risk_score": c.get("fraud_risk_score", 0.0),
        })
    print(f"  {len(customers)} customers loaded")
    return len(customers)

async def _load_sellers(sellers: list[dict]) -> int:
    from graphrag.neo4j_client import upsert_node
    print(f"Loading {len(sellers)} sellers...")
    for s in sellers:
        await upsert_node("Seller", "id", {
            "id": s["id"],
            "name": s["name"],
            "dispute_rate": s.get("dispute_rate", 0.0),
            "refund_rate": s.get("refund_rate", 0.0),
            "fraud_signals": s.get("fraud_signals", 0),
        })
    print(f"  {len(sellers)} sellers loaded")
    return len(sellers)

async def _load_products(products: list[dict]) -> int:
    from graphrag.neo4j_client import upsert_node, upsert_relationship
    from ingestion.embedder import embed_texts

    print(f"Loading {len(products)} products with embeddings...")
    texts = [f"{p['name']} {p['category']}" for p in products]
    embeddings = await embed_texts(texts)

    for p, emb in zip(products, embeddings):
        await upsert_node("Product", "sku", {
            "sku": p["sku"],
            "name": p["name"],
            "category": p["category"],
            "price_gbp": p.get("price_gbp", 0.0),
            "defect_rate": p.get("defect_rate", 0.0),
            "return_rate": p.get("return_rate", 0.0),
            "embedding": emb,
        })
        if p.get("seller_id"):
            await upsert_relationship(
                "Product", "sku", p["sku"],
                "SOLD_BY",
                "Seller", "id", p["seller_id"],
            )

    print(f"  {len(products)} products loaded")
    return len(products)

async def _load_disputes(disputes: list[dict], batch_size: int = 20) -> int:
    from graphrag.neo4j_client import upsert_node, upsert_relationship
    from ingestion.embedder import embed_texts
    from ingestion.deduplicator import is_duplicate, mark_ingested

    print(f"Loading {len(disputes)} disputes with embeddings (batch_size={batch_size})...")
    loaded = 0

    for i in range(0, len(disputes), batch_size):
        batch = disputes[i: i + batch_size]
        new_batch = [r for r in batch if not is_duplicate({"dispute_id": r["dispute"]["id"]})]

        if not new_batch:
            loaded += len(batch)
            continue

        texts = [r["dispute"]["description"] for r in new_batch]
        embeddings = await embed_texts(texts)

        for record, emb in zip(new_batch, embeddings):
            disp = record["dispute"]
            order = record["order"]

            await upsert_node("Order", "id", order)

            await upsert_node("Dispute", "id", {
                "id": disp["id"],
                "category": disp["category"],
                "channel": disp["channel"],
                "status": disp["status"],
                "resolution": disp["resolution"],
                "confidence": disp["confidence"],
                "description": disp["description"],
                "embedding": emb,
                "created_at": disp.get("created_at", ""),
            })

            await upsert_relationship("Customer", "id", record["customer_id"], "PLACED", "Order", "id", order["id"])
            await upsert_relationship("Order", "id", order["id"], "CONTAINS", "Product", "sku", record["product_sku"])
            await upsert_relationship("Customer", "id", record["customer_id"], "RAISED", "Dispute", "id", disp["id"])
            await upsert_relationship("Dispute", "id", disp["id"], "CONCERNS", "Order", "id", order["id"])

            for ev in record.get("evidence", []):
                await upsert_node("Evidence", "id", ev)
                await upsert_relationship("Dispute", "id", disp["id"], "SUPPORTED_BY", "Evidence", "id", ev["id"])

            mark_ingested({"dispute_id": disp["id"]})
            loaded += 1

        print(f"  {min(i + batch_size, len(disputes))}/{len(disputes)} disputes embedded and loaded...")

    print(f"  {loaded} disputes loaded")
    return loaded

async def _load_policies(policies: list[dict]) -> int:
    from ingestion.policy_ingester import ingest_policy
    from datetime import datetime
    print(f"Loading {len(policies)} seller policies...")
    for p in policies:
        await ingest_policy(
            policy_id=p["id"],
            source=p["source"],
            clause=p["clause"],
            text=p["text"],
            seller_id=p.get("seller_id"),
            version_date=datetime.fromisoformat(p.get("version_date", "2024-01-01T00:00:00")),
        )
    print(f"  {len(policies)} seller policies loaded")
    return len(policies)

async def _load_legal_clauses() -> int:
    from ingestion.policy_ingester import ingest_legal_clauses
    print("Loading Consumer Rights Act 2015 clauses...")
    n = await ingest_legal_clauses()
    print(f"  {n} legal clauses loaded")
    return n

async def _compute_similarity_edges() -> None:
    from graphrag.neo4j_client import run_write
    print("Computing SIMILAR_TO edges (cosine > 0.75 using Neo4j GDS)...")
    try:
        await run_write("""
            MATCH (d1:Dispute), (d2:Dispute)
            WHERE d1.id < d2.id
              AND d1.embedding IS NOT NULL
              AND d2.embedding IS NOT NULL
              AND d1.category = d2.category
            WITH d1, d2,
                 gds.similarity.cosine(d1.embedding, d2.embedding) AS score
            WHERE score > 0.75
            MERGE (d1)-[r:SIMILAR_TO]->(d2)
            SET r.score = score
        """)
        print("  SIMILAR_TO edges created")
    except Exception as e:
        print(f"  Warning: GDS similarity failed ({e}). Install Neo4j GDS plugin to enable.")

async def _resolve_policy_links() -> None:
    from graphrag.neo4j_client import run_query, upsert_relationship
    print("Linking resolved disputes to applicable policy clauses...")

    disputes = await run_query("""
        MATCH (d:Dispute {status: 'resolved'})
        WHERE NOT (d)-[:RESOLVED_BY]->(:Policy)
        RETURN d.id AS did, d.category AS category
        LIMIT 500
    """)

    policies = await run_query("MATCH (p:Policy) RETURN p.id AS pid LIMIT 20")
    if not policies:
        print("  No policies found — run law ingestion first")
        return

    policy_ids = [p["pid"] for p in policies]
    for d in disputes:
        pol_id = policy_ids[hash(d["did"]) % len(policy_ids)]
        await upsert_relationship("Dispute", "id", d["did"], "RESOLVED_BY", "Policy", "id", pol_id)

    print(f"  Linked {len(disputes)} disputes to policy clauses")

def _load_json(filename: str) -> list:
    path = DATA_DIR / filename
    if not path.exists():
        print(f"  WARNING: {path} not found — run python scripts/generate_data.py first")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

async def main(only: str | None = None, skip_sim: bool = False):
    await _apply_schema()

    if only == "laws":
        await _load_legal_clauses()
        return

    customers = _load_json("customers.json")
    sellers = _load_json("sellers.json")
    products = _load_json("products.json")
    disputes = _load_json("disputes.json")
    policies = _load_json("policies.json")

    await _load_customers(customers)
    await _load_sellers(sellers)
    await _load_products(products)
    await _load_legal_clauses()
    await _load_policies(policies)
    await _load_disputes(disputes, batch_size=25)
    await _resolve_policy_links()

    if not skip_sim:
        await _compute_similarity_edges()

    print("\n✓ All data loaded. Graph ready for GraphRAG retrieval.")
    print("  Next: python main.py communities  — build community summaries")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["laws"], help="Load only this subset")
    parser.add_argument("--skip-sim", action="store_true", help="Skip SIMILAR_TO edge computation")
    args = parser.parse_args()
    asyncio.run(main(only=args.only, skip_sim=args.skip_sim))
