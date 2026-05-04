from graphrag.neo4j_client import run_query
from production.monitoring import trace_node
from production.rate_limiter import with_retry

@with_retry()
@trace_node("precedent_agent")
async def precedent_agent(state: dict) -> dict:
    case_id = state.get("case_id", "")
    customer_id = state.get("customer_id", "")
    category = state.get("dispute_category", "")
    order_id = state.get("order_id", "")

    traversal_records = await run_query(
        """
        MATCH (c:Customer {id: $customer_id})-[:RAISED]->(d:Dispute {category: $category})
              -[:SIMILAR_TO]->(similar:Dispute {status: 'resolved'})
        OPTIONAL MATCH (similar)-[:CONCERNS]->(o:Order)-[:CONTAINS]->(p:Product)
        RETURN similar.id AS case_id,
               similar.resolution AS resolution,
               similar.confidence AS confidence,
               p.category AS product_category,
               gds.similarity.cosine(d.embedding, similar.embedding) AS similarity
        ORDER BY similarity DESC
        LIMIT 5
        """,
        {"customer_id": customer_id, "category": category},
    )

    if not traversal_records:
        traversal_records = await run_query(
            """
            MATCH (d:Dispute {category: $category, status: 'resolved'})
            OPTIONAL MATCH (d)-[:CONCERNS]->(o:Order)-[:CONTAINS]->(p:Product)
            RETURN d.id AS case_id,
                   d.resolution AS resolution,
                   d.confidence AS confidence,
                   p.category AS product_category,
                   0.75 AS similarity
            ORDER BY d.confidence DESC
            LIMIT 5
            """,
            {"category": category},
        )

    precedents = []
    for r in traversal_records:
        precedents.append({
            "case_id": r.get("case_id", ""),
            "resolution": r.get("resolution", "unknown"),
            "confidence": r.get("confidence", 0.0),
            "product_category": r.get("product_category", ""),
            "similarity": round(float(r.get("similarity") or 0.0), 4),
        })

    sku_signal = await _check_product_defect_pattern(order_id, category)

    return {
        "precedent_cases": precedents,
        "graph_subgraph": {
            **state.get("graph_subgraph", {}),
            "sku_defect_signal": sku_signal,
        },
    }

async def _check_product_defect_pattern(order_id: str, category: str) -> dict:
    if not order_id:
        return {}
    records = await run_query(
        """
        MATCH (o:Order {id: $order_id})-[:CONTAINS]->(p:Product)
              <-[:CONTAINS]-(:Order)<-[:CONCERNS]-(d:Dispute {category: $category})
        RETURN p.sku AS sku, p.name AS name,
               count(d) AS dispute_count,
               p.defect_rate AS defect_rate
        LIMIT 1
        """,
        {"order_id": order_id, "category": category},
    )
    if records:
        return records[0]
    return {}
