import os

from ingestion.embedder import embed_single
from graphrag.subgraph_retriever import retrieve_subgraph, retrieve_policy_nodes
from graphrag.graph_serialiser import serialise_subgraph
from production.cache import cached
from production.monitoring import trace_node
from production.rate_limiter import with_retry

@cached()
@with_retry()
@trace_node("policy_retrieval")
async def policy_retrieval(state: dict) -> dict:
    case_id = state.get("case_id", "unknown")
    customer_id = state.get("customer_id", "")
    order_id = state.get("order_id", "")
    category = state.get("dispute_category", "")

    history = state.get("channel_history", [])
    query_text = " ".join(e.get("content", "") for e in history[-3:])
    query_text = f"{category} dispute: {query_text}"

    query_vector = await embed_single(query_text)
    cohere_key = os.getenv("COHERE_API_KEY", "")

    subgraph_results = await retrieve_subgraph(
        case_id=case_id,
        customer_id=customer_id,
        order_id=order_id,
        query_vector=query_vector,
        cohere_api_key=cohere_key,
        query_text=query_text,
    )

    policy_results = await retrieve_policy_nodes(query_vector)

    policy_findings = []
    legal_citations = []

    for result in policy_results[:10]:
        data = result.data
        if result.node_type in ("Policy", "policy"):
            policy_findings.append({
                "clause": data.get("clause", ""),
                "source": data.get("source", ""),
                "text": data.get("text", "")[:500],
                "relevance_score": round(result.score, 4),
                "version_date": data.get("version_date", ""),
            })
        elif result.node_type in ("LegalClause", "legalclause"):
            citation = f"{data.get('act')} {data.get('section')}"
            if citation not in legal_citations:
                legal_citations.append(citation)
            policy_findings.append({
                "clause": data.get("section", ""),
                "source": data.get("act", ""),
                "text": data.get("text", "")[:500],
                "relevance_score": round(result.score, 4),
                "version_date": "",
            })

    graph_context = {
        "serialised": serialise_subgraph(subgraph_results, max_nodes=15),
        "order_value": 0.0,
    }

    return {
        "policy_findings": policy_findings,
        "legal_citations": legal_citations,
        "graph_subgraph": graph_context,
    }
