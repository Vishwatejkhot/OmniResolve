import time
from typing import Any

import cohere

from graphrag.neo4j_client import run_query
from graphrag.rrf_fusion import RankedResult, reciprocal_rank_fusion
from production import audit_logger
from production.cache import cached
from production.rate_limiter import with_retry

def _to_results(records: list[dict], node_key: str, node_type: str) -> list[RankedResult]:
    results = []
    for i, r in enumerate(records):
        node = r.get(node_key, {})
        node_id = node.get("id") or node.get("sku") or node.get("community_id") or str(i)
        results.append(RankedResult(node_id=str(node_id), node_type=node_type, data=node))
    return results

@with_retry()
async def _local_subgraph(customer_id: str, order_id: str) -> list[RankedResult]:
    cypher = """
        MATCH (c:Customer {id: $customer_id})-[:RAISED]->(d:Dispute)
              -[:CONCERNS]->(o:Order {id: $order_id})-[:CONTAINS]->(p:Product)
              -[:SOLD_BY]->(s:Seller)
        OPTIONAL MATCH (d)-[:RESOLVED_BY]->(pol:Policy)
        OPTIONAL MATCH (d)-[:CITES]->(lc:LegalClause)
        RETURN d AS dispute, p AS product, s AS seller,
               collect(DISTINCT pol) AS policies,
               collect(DISTINCT lc) AS legal_clauses
        LIMIT 20
    """
    records = await run_query(cypher, {"customer_id": customer_id, "order_id": order_id})
    return _to_results(records, "dispute", "Dispute")

@with_retry()
async def _community_retrieval(query_vector: list[float], top_k: int = 5) -> list[RankedResult]:
    cypher = """
        CALL db.index.vector.queryNodes('community_embeddings', $top_k, $vector)
        YIELD node AS cs, score
        RETURN cs AS community_summary, score
        ORDER BY score DESC
    """
    records = await run_query(cypher, {"top_k": top_k, "vector": query_vector})
    results = []
    for r in records:
        cs = r.get("community_summary", {})
        results.append(RankedResult(
            node_id=f"community_{cs.get('community_id', 0)}",
            node_type="CaseSummary",
            data=cs,
            score=r.get("score", 0.0),
        ))
    return results

@with_retry()
async def _vector_similarity(query_vector: list[float], index: str, top_k: int = 10) -> list[RankedResult]:
    cypher = """
        CALL db.index.vector.queryNodes($index, $top_k, $vector)
        YIELD node, score
        RETURN node, score
        ORDER BY score DESC
    """
    records = await run_query(cypher, {"index": index, "top_k": top_k, "vector": query_vector})
    results = []
    for r in records:
        node = r.get("node", {})
        node_id = node.get("id") or node.get("sku") or node.get("community_id") or "unknown"
        label = index.replace("-embeddings", "").replace("_embeddings", "").title()
        results.append(RankedResult(
            node_id=str(node_id),
            node_type=label,
            data=node,
            score=r.get("score", 0.0),
        ))
    return results

@cached()
@with_retry()
async def retrieve_subgraph(
    case_id: str,
    customer_id: str,
    order_id: str,
    query_vector: list[float],
    cohere_api_key: str,
    query_text: str,
) -> list[RankedResult]:
    t0 = time.monotonic()

    local, community, vector = await _run_all_modes(customer_id, order_id, query_vector)

    fused = reciprocal_rank_fusion(local, community, vector)

    if cohere_api_key and fused:
        fused = await _cohere_rerank(fused, query_text, cohere_api_key)

    latency_ms = (time.monotonic() - t0) * 1000
    audit_logger.log_graphrag_retrieval(case_id, "fused_rrf", len(fused), latency_ms)
    return fused

async def _run_all_modes(
    customer_id: str,
    order_id: str,
    query_vector: list[float],
) -> tuple[list[RankedResult], list[RankedResult], list[RankedResult]]:
    import asyncio
    local_task = asyncio.create_task(_local_subgraph(customer_id, order_id))
    community_task = asyncio.create_task(_community_retrieval(query_vector))
    vector_task = asyncio.create_task(_vector_similarity(query_vector, "dispute_embeddings"))
    return await asyncio.gather(local_task, community_task, vector_task)

async def _cohere_rerank(
    results: list[RankedResult],
    query: str,
    api_key: str,
) -> list[RankedResult]:
    co = cohere.Client(api_key)
    docs = [f"{r.node_type}: {r.data}" for r in results]
    response = co.rerank(model="rerank-v3.5", query=query, documents=docs, top_n=len(docs))
    reranked: list[RankedResult] = []
    for hit in response.results:
        r = results[hit.index]
        r.score = hit.relevance_score
        reranked.append(r)
    return reranked

async def retrieve_policy_nodes(query_vector: list[float], top_k: int = 8) -> list[RankedResult]:
    import asyncio
    policy_task = asyncio.create_task(_vector_similarity(query_vector, "policy_embeddings", top_k))
    legal_task = asyncio.create_task(_vector_similarity(query_vector, "legal_embeddings", top_k))
    policies, legals = await asyncio.gather(policy_task, legal_task)
    return reciprocal_rank_fusion(policies, legals)
