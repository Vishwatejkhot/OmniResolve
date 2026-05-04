import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from agents.orchestrator import get_compiled_graph
from channels.document_handler import save_upload

router = APIRouter()

class NewCaseRequest(BaseModel):
    customer_id: str = ""
    order_id: str = ""
    session_id: str = ""
    channel: str = "web"
    message: str

class HumanDecisionRequest(BaseModel):
    resolution: str
    notes: str = ""

@router.post("/")
async def create_case(req: NewCaseRequest) -> dict[str, Any]:
    case_id = f"case_{uuid.uuid4().hex[:10]}"
    session_id = req.session_id or case_id

    initial_state = {
        "case_id": case_id,
        "customer_id": req.customer_id,
        "order_id": req.order_id,
        "session_id": session_id,
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
            "channel": req.channel,
            "content": req.message,
            "sender": req.customer_id,
        }],
    }

    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": case_id}}
    final_state = await graph.ainvoke(initial_state, config=config)

    return {
        "case_id": case_id,
        "resolution": final_state.get("resolution_recommendation"),
        "confidence": final_state.get("confidence_score"),
        "requires_human": final_state.get("requires_human"),
        "legal_citations": final_state.get("legal_citations", []),
        "brief": final_state.get("graph_subgraph", {}).get("resolution_brief", ""),
    }

@router.get("/{case_id}")
async def get_case(case_id: str) -> dict[str, Any]:
    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": case_id}}
    state = await graph.aget_state(config)
    if not state or not state.values:
        raise HTTPException(status_code=404, detail="Case not found")
    values = state.values
    return {
        "case_id": case_id,
        "dispute_category": values.get("dispute_category"),
        "resolution": values.get("resolution_recommendation"),
        "confidence": values.get("confidence_score"),
        "requires_human": values.get("requires_human"),
        "legal_citations": values.get("legal_citations", []),
        "precedent_cases": values.get("precedent_cases", []),
    }

@router.post("/{case_id}/human-decision")
async def submit_human_decision(case_id: str, decision: HumanDecisionRequest) -> dict:
    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": case_id}}
    await graph.aupdate_state(config, {"human_decision": decision.model_dump()})
    final_state = await graph.ainvoke(None, config=config)
    return {
        "case_id": case_id,
        "resolution": final_state.get("resolution_recommendation"),
        "human_reviewed": final_state.get("graph_subgraph", {}).get("human_reviewed", False),
    }

@router.post("/{case_id}/evidence")
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
) -> dict:
    file_bytes = await file.read()
    doc = save_upload(file_bytes, file.filename or "upload")
    doc["case_id"] = case_id

    graph = await get_compiled_graph()
    config = {"configurable": {"thread_id": case_id}}
    state = await graph.aget_state(config)
    if state and state.values:
        existing = state.values.get("documents", [])
        await graph.aupdate_state(config, {"documents": existing + [doc]})

    return {"doc_id": doc["id"], "type": doc["type"], "case_id": case_id}

@router.get("/")
async def list_cases() -> dict:
    return {"message": "Case listing requires direct Neo4j query — see /api/v1/cases/stats"}
