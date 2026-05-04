import os
import json
from pathlib import Path
from typing import Any

import anthropic
import numpy as np

from graphrag.neo4j_client import run_query
from graphrag.graph_serialiser import serialise_case_context
from production.audit_logger import log_resolution
from production.cache import cached
from production.monitoring import trace_node
from production.rate_limiter import with_anthropic_rate_limit, with_retry

try:
    import xgboost as xgb
    _XGB_AVAILABLE = True
except ImportError:
    _XGB_AVAILABLE = False

_MODEL_PATH = Path("models/resolution_classifier.json")
_LABEL_MAP = {0: "refund", 1: "replace", 2: "reject", 3: "escalate"}
_CATEGORY_MAP = {"fraud": 0, "damage": 1, "non_delivery": 2, "other": 3}

_RESOLUTION_SYSTEM = """You are a senior dispute resolution specialist for an e-commerce platform.
You have full context: the customer's history, the product, the seller's track record, applicable
UK consumer law (Consumer Rights Act 2015), precedent cases, and physical evidence scores.

Your task: write a professional resolution brief for the caseworker that includes:
1. Recommended action (refund / replace / reject / escalate) and why
2. The specific Consumer Rights Act 2015 clause(s) that apply
3. How the precedent cases support your recommendation
4. Any fraud or systemic risk flags
5. A plain-English explanation for the customer (2-3 sentences)

Be precise, cite specific sections, and keep the brief under 400 words."""

def _load_xgb_model() -> "xgb.XGBClassifier | None":
    if not _XGB_AVAILABLE or not _MODEL_PATH.exists():
        return None
    model = xgb.XGBClassifier()
    model.load_model(str(_MODEL_PATH))
    return model

_xgb_model = _load_xgb_model()

def _extract_features(state: dict, graph_context: dict) -> np.ndarray:
    evidence = state.get("evidence_scores", {})
    top_evidence = next(iter(evidence.values()), {}) if evidence else {}
    precedents = state.get("precedent_cases", [{}])
    policies = state.get("policy_findings", [{}])

    features = [
        _CATEGORY_MAP.get(state.get("dispute_category", "other"), 3),
        float(graph_context.get("customer_dispute_count", 0)),
        float(graph_context.get("customer_fraud_risk_score", 0.0)),
        float(graph_context.get("seller_refund_rate", 0.0)),
        float(graph_context.get("seller_dispute_rate", 0.0)),
        float(graph_context.get("product_defect_rate", 0.0)),
        float(graph_context.get("product_return_rate", 0.0)),
        float(top_evidence.get("damage_score", 0.0)),
        float(top_evidence.get("validity_score", 0.0)),
        float(policies[0].get("relevance_score", 0.0) if policies else 0.0),
        float(precedents[0].get("similarity", 0.0) if precedents else 0.0),
        float(graph_context.get("order_value", 0.0)),
        float(graph_context.get("days_since_purchase", 30)),
    ]
    return np.array([features], dtype=np.float32)

async def _fetch_graph_context(customer_id: str, order_id: str) -> dict:
    records = await run_query(
        """
        MATCH (c:Customer {id: $customer_id})-[:PLACED]->(o:Order {id: $order_id})
              -[:CONTAINS]->(p:Product)-[:SOLD_BY]->(s:Seller)
        RETURN c.dispute_count AS customer_dispute_count,
               c.fraud_risk_score AS customer_fraud_risk_score,
               s.refund_rate AS seller_refund_rate,
               s.dispute_rate AS seller_dispute_rate,
               p.defect_rate AS product_defect_rate,
               p.return_rate AS product_return_rate,
               o.total_value AS order_value,
               duration.between(o.date, datetime()).days AS days_since_purchase,
               c, o, p, s
        LIMIT 1
        """,
        {"customer_id": customer_id, "order_id": order_id},
    )
    return records[0] if records else {}

@with_retry()
@with_anthropic_rate_limit
@trace_node("resolution_engine")
async def resolution_engine(state: dict) -> dict:
    case_id = state.get("case_id", "unknown")
    customer_id = state.get("customer_id", "")
    order_id = state.get("order_id", "")

    graph_context = await _fetch_graph_context(customer_id, order_id)

    xgb_recommendation = "refund"
    xgb_confidence = 0.75

    if _xgb_model is not None:
        features = _extract_features(state, graph_context)
        proba = _xgb_model.predict_proba(features)[0]
        xgb_label = int(np.argmax(proba))
        xgb_recommendation = _LABEL_MAP[xgb_label]
        xgb_confidence = float(proba[xgb_label])

    customer_data = {k: graph_context.get(k) for k in ("customer_dispute_count", "customer_fraud_risk_score")}
    customer_data["id"] = customer_id
    customer_data["name"] = graph_context.get("c", {}).get("name", "Customer")

    case_context = serialise_case_context(
        customer={"id": customer_id, **graph_context.get("c", {}), **customer_data},
        order=graph_context.get("o", {"id": order_id}),
        product=graph_context.get("p", {}),
        seller=graph_context.get("s", {}),
        disputes=[],
        policy_findings=state.get("policy_findings", []),
        precedents=state.get("precedent_cases", []),
    )

    subgraph_text = state.get("graph_subgraph", {}).get("serialised", "")
    evidence_summary = json.dumps(state.get("evidence_scores", {}), indent=2)[:800]

    prompt = (
        f"{case_context}\n\n"
        f"## GRAPH CONTEXT\n{subgraph_text}\n\n"
        f"## EVIDENCE ANALYSIS\n{evidence_summary}\n\n"
        f"## XGBoost Recommendation\n{xgb_recommendation} (confidence: {xgb_confidence:.2f})\n\n"
        f"Write the resolution brief:"
    )

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=_RESOLUTION_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    brief = response.content[0].text.strip()
    final_confidence = (xgb_confidence + state.get("confidence_score", 0.75)) / 2.0
    requires_human = final_confidence < 0.65 or xgb_recommendation == "escalate"

    log_resolution(
        case_id=case_id,
        customer_id=customer_id,
        dispute_category=state.get("dispute_category", "unknown"),
        recommendation=xgb_recommendation,
        confidence=final_confidence,
        legal_citations=state.get("legal_citations", []),
        agent_path=["channel_normaliser", "customer_resolver", "dispute_classifier",
                    "policy_retrieval", "evidence_analyser", "precedent_agent", "resolution_engine"],
        policy_sources=[p.get("source", "") for p in state.get("policy_findings", [])],
    )

    return {
        "resolution_recommendation": xgb_recommendation,
        "confidence_score": final_confidence,
        "requires_human": requires_human,
        "graph_subgraph": {**state.get("graph_subgraph", {}), "resolution_brief": brief, **graph_context},
    }
