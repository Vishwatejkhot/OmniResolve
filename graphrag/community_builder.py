import os
from typing import Any

import anthropic

from graphrag.neo4j_client import run_query, run_write, upsert_node
from ingestion.embedder import embed_texts

_GRAPH_NAME = "dispute_graph"

async def project_graph() -> None:
    await run_write(f"""
        CALL gds.graph.drop('{_GRAPH_NAME}', false) YIELD graphName
    """)
    await run_write(f"""
        CALL gds.graph.project(
            '{_GRAPH_NAME}',
            ['Dispute', 'Customer', 'Product', 'Seller'],
            {{
                RAISED: {{orientation: 'UNDIRECTED'}},
                CONCERNS: {{orientation: 'UNDIRECTED'}},
                SIMILAR_TO: {{orientation: 'UNDIRECTED', properties: ['score']}}
            }}
        )
    """)

async def run_louvain() -> list[dict[str, Any]]:
    records = await run_query(f"""
        CALL gds.louvain.write('{_GRAPH_NAME}', {{
            writeProperty: 'communityId',
            maxIterations: 10
        }})
        YIELD communityCount, modularity
        RETURN communityCount, modularity
    """)
    return records

async def get_community_disputes(community_id: int, limit: int = 50) -> list[dict]:
    records = await run_query("""
        MATCH (d:Dispute {communityId: $cid})
        OPTIONAL MATCH (d)-[:CONCERNS]->(o:Order)-[:CONTAINS]->(p:Product)
        OPTIONAL MATCH (d)-[:RESOLVED_BY]->(pol:Policy)
        RETURN d.id AS dispute_id, d.category AS category,
               d.resolution AS resolution, p.name AS product,
               pol.clause AS policy_clause
        LIMIT $limit
    """, {"cid": community_id, "limit": limit})
    return records

async def generate_community_summary(community_id: int, disputes: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    dispute_text = "\n".join(
        f"- [{d.get('category')}] Product: {d.get('product', 'N/A')} | "
        f"Resolution: {d.get('resolution', 'pending')} | "
        f"Policy: {d.get('policy_clause', 'N/A')}"
        for d in disputes[:30]
    )
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        messages=[{
            "role": "user",
            "content": (
                f"You are summarising a cluster of {len(disputes)} related e-commerce disputes "
                f"for a retrieval index. Write a 3-4 sentence summary identifying the common "
                f"patterns, product categories, dispute types, and typical resolutions.\n\n"
                f"Disputes:\n{dispute_text}"
            ),
        }],
    )
    return response.content[0].text

async def build_all_communities() -> int:
    await project_graph()
    stats = await run_louvain()
    community_count = stats[0]["communityCount"] if stats else 0

    community_ids_raw = await run_query("""
        MATCH (d:Dispute)
        WHERE d.communityId IS NOT NULL
        RETURN DISTINCT d.communityId AS cid, count(d) AS n
        ORDER BY n DESC
    """)

    summaries_created = 0
    for row in community_ids_raw:
        cid = row["cid"]
        disputes = await get_community_disputes(cid)
        if not disputes:
            continue
        summary_text = await generate_community_summary(cid, disputes)
        embeddings = await embed_texts([summary_text])
        node_data = {
            "community_id": cid,
            "summary": summary_text,
            "embedding": embeddings[0],
            "case_count": len(disputes),
        }
        await upsert_node("CaseSummary", "community_id", node_data)
        summaries_created += 1

    return summaries_created
