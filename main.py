"""
OmniResolve — Unified Omnichannel E-Commerce Dispute Intelligence System

Entry points:
  python main.py api            — start FastAPI server
  python main.py dashboard      — start Streamlit dashboard
  python main.py seed           — seed Neo4j with 500 synthetic cases
  python main.py ingest-laws    — ingest Consumer Rights Act 2015 clauses
  python main.py communities    — run community detection + LLM summaries
  python main.py run-case       — run a single demo case through the pipeline
"""
import asyncio
import sys

def _start_api():
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=8000, reload=True)

def _start_dashboard():
    import subprocess
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "dashboard/app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
    ])

async def _seed():
    from dotenv import load_dotenv
    load_dotenv()
    from graphrag.neo4j_client import apply_schema
    from ingestion.case_ingester import load_from_json, seed_graph
    from ingestion.policy_ingester import ingest_legal_clauses
    from pathlib import Path

    print("Applying Neo4j schema...")
    await apply_schema()

    print("Ingesting Consumer Rights Act 2015 clauses...")
    n = await ingest_legal_clauses()
    print(f"  {n} legal clauses ingested.")

    if Path("data/disputes.json").exists():
        print("Loading rich dispute data from data/disputes.json...")
        count = await load_from_json("data/disputes.json")
    else:
        print("data/disputes.json not found — run: python scripts/generate_data.py")
        print("Falling back to basic synthetic seed...")
        count = await seed_graph(500)
    print(f"  {count} cases seeded.")
    print("Done.")

async def _ingest_laws():
    from dotenv import load_dotenv
    load_dotenv()
    from graphrag.neo4j_client import apply_schema
    from ingestion.policy_ingester import ingest_legal_clauses

    await apply_schema()
    n = await ingest_legal_clauses()
    print(f"Ingested {n} legal clauses.")

async def _build_communities():
    from dotenv import load_dotenv
    load_dotenv()
    from graphrag.community_builder import build_all_communities

    print("Building community summaries...")
    n = await build_all_communities()
    print(f"Created {n} community summary nodes.")

async def _demo_case():
    from dotenv import load_dotenv
    load_dotenv()
    import uuid
    from agents.orchestrator import get_compiled_graph

    case_id = f"demo_{uuid.uuid4().hex[:8]}"
    print(f"\nRunning demo case: {case_id}")

    initial_state = {
        "case_id": case_id,
        "customer_id": "",
        "order_id": "",
        "session_id": case_id,
        "channel_history": [],
        "documents": [],
        "evidence_scores": {},
        "dispute_category": "",
        "policy_findings": [],
        "legal_citations": [],
        "precedent_cases": [],
        "graph_subgraph": {},
        "resolution_recommendation": "",
        "confidence_score": 0.0,
        "requires_human": False,
        "cache_key": "",
        "retry_count": 0,
        "error_log": [],
        "_raw_events": [{
            "channel": "chat",
            "content": (
                "Hello, I ordered a pair of headphones (order ord_demo0001) three weeks ago "
                "and they arrived completely broken. The box was damaged and one ear cup is "
                "cracked. I have photos. I want a full refund under the Consumer Rights Act."
            ),
            "sender": "demo.customer@example.com",
        }],
    }

    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": case_id}}
    final = await graph.ainvoke(initial_state, config=config)

    print("\n" + "="*60)
    print(f"Category:       {final.get('dispute_category')}")
    print(f"Recommendation: {final.get('resolution_recommendation')}")
    print(f"Confidence:     {final.get('confidence_score', 0):.2f}")
    print(f"Requires human: {final.get('requires_human')}")
    print(f"Legal citations: {', '.join(final.get('legal_citations', []))}")
    brief = final.get("graph_subgraph", {}).get("resolution_brief", "")
    if brief:
        print("\nResolution Brief:\n" + brief)
    print("="*60)

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "api"

    if cmd == "api":
        _start_api()
    elif cmd == "dashboard":
        _start_dashboard()
    elif cmd == "seed":
        asyncio.run(_seed())
    elif cmd == "ingest-laws":
        asyncio.run(_ingest_laws())
    elif cmd == "communities":
        asyncio.run(_build_communities())
    elif cmd == "run-case":
        asyncio.run(_demo_case())
    else:
        print(__doc__)
        sys.exit(1)

if __name__ == "__main__":
    main()
