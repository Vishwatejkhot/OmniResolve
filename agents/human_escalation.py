import asyncio
import json
from datetime import datetime, timezone

from production.audit_logger import log_escalation
from production.monitoring import trace_node

@trace_node("human_escalation")
async def human_escalation(state: dict) -> dict:
    case_id = state.get("case_id", "unknown")
    confidence = state.get("confidence_score", 0.0)

    escalation_brief = _build_escalation_brief(state)

    log_escalation(
        case_id=case_id,
        reason=_escalation_reason(state),
        confidence=confidence,
    )

    human_decision = state.get("human_decision")
    if human_decision:
        resolution = human_decision.get("resolution", state.get("resolution_recommendation"))
        notes = human_decision.get("notes", "")
        return {
            "resolution_recommendation": resolution,
            "confidence_score": 1.0,
            "requires_human": False,
            "graph_subgraph": {
                **state.get("graph_subgraph", {}),
                "human_reviewed": True,
                "human_notes": notes,
                "reviewed_at": datetime.now(timezone.utc).isoformat(),
            },
        }

    return {
        "graph_subgraph": {
            **state.get("graph_subgraph", {}),
            "escalation_brief": escalation_brief,
            "escalated_at": datetime.now(timezone.utc).isoformat(),
        },
    }

def _escalation_reason(state: dict) -> str:
    reasons = []
    if state.get("confidence_score", 1.0) < 0.65:
        reasons.append(f"low confidence ({state['confidence_score']:.2f})")
    if state.get("resolution_recommendation") == "escalate":
        reasons.append("XGBoost flagged for escalation")
    graph = state.get("graph_subgraph", {})
    if float(graph.get("order_value", 0)) > 200:
        reasons.append(f"high-value order £{graph['order_value']:.2f}")
    return "; ".join(reasons) or "policy threshold"

def _build_escalation_brief(state: dict) -> str:
    lines = [
        f"ESCALATION BRIEF — Case {state.get('case_id')}",
        f"Customer: {state.get('customer_id')}  |  Order: {state.get('order_id')}",
        f"Category: {state.get('dispute_category')}  |  Confidence: {state.get('confidence_score', 0):.2f}",
        f"System recommendation: {state.get('resolution_recommendation')}",
        "",
        "Reason for escalation:",
        f"  {_escalation_reason(state)}",
        "",
    ]
    brief = state.get("graph_subgraph", {}).get("resolution_brief", "")
    if brief:
        lines += ["Agent resolution brief:", brief]
    lines += [
        "",
        "Legal citations: " + ", ".join(state.get("legal_citations", [])),
        "",
        "Actions available: refund | replace | reject | escalate_to_trading_standards",
    ]
    return "\n".join(lines)
