import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_DIR = Path("logs")
_LOG_DIR.mkdir(exist_ok=True)

_file_handler = logging.FileHandler(_LOG_DIR / "audit.jsonl", encoding="utf-8")
_file_handler.setLevel(logging.INFO)

_stream_handler = logging.StreamHandler(sys.stdout)
_stream_handler.setLevel(logging.INFO)

_logger = logging.getLogger("omni_resolve.audit")
_logger.setLevel(logging.INFO)
_logger.addHandler(_file_handler)
_logger.addHandler(_stream_handler)
_logger.propagate = False

def _emit(event_type: str, payload: dict[str, Any]) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_type,
        **payload,
    }
    _logger.info(json.dumps(record))

def log_resolution(
    case_id: str,
    customer_id: str,
    dispute_category: str,
    recommendation: str,
    confidence: float,
    legal_citations: list[str],
    agent_path: list[str],
    policy_sources: list[str],
) -> None:
    _emit("resolution", {
        "case_id": case_id,
        "customer_id": customer_id,
        "dispute_category": dispute_category,
        "recommendation": recommendation,
        "confidence": confidence,
        "legal_citations": legal_citations,
        "agent_path": agent_path,
        "policy_sources": policy_sources,
    })

def log_escalation(case_id: str, reason: str, confidence: float) -> None:
    _emit("escalation", {"case_id": case_id, "reason": reason, "confidence": confidence})

def log_evidence(case_id: str, doc_id: str, damage_score: float, validity_score: float) -> None:
    _emit("evidence", {
        "case_id": case_id,
        "doc_id": doc_id,
        "damage_score": damage_score,
        "validity_score": validity_score,
    })

def log_graphrag_retrieval(case_id: str, mode: str, nodes_returned: int, latency_ms: float) -> None:
    _emit("graphrag_retrieval", {
        "case_id": case_id,
        "mode": mode,
        "nodes_returned": nodes_returned,
        "latency_ms": latency_ms,
    })

def log_error(case_id: str, node: str, error: str) -> None:
    _emit("error", {"case_id": case_id, "node": node, "error": error})
