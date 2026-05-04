import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import numpy as np

@pytest.mark.asyncio
async def test_resolution_engine_no_xgb():
    with patch("agents.resolution_engine._fetch_graph_context", new_callable=AsyncMock) as mock_ctx, \
         patch("agents.resolution_engine.anthropic.Anthropic") as mock_cls, \
         patch("agents.resolution_engine._xgb_model", None):

        mock_ctx.return_value = {
            "c": {"id": "c1", "name": "Alice"},
            "o": {"id": "ord_001", "total_value": 50.0, "status": "delivered",
                  "channel": "web", "date": "2025-01-01"},
            "p": {"sku": "SKU-1", "name": "Widget", "category": "electronics",
                  "defect_rate": 0.01, "return_rate": 0.05},
            "s": {"id": "s1", "name": "Seller", "dispute_rate": 0.03,
                  "refund_rate": 0.06, "fraud_signals": 0},
            "customer_dispute_count": 1,
            "customer_fraud_risk_score": 0.05,
            "seller_refund_rate": 0.06,
            "seller_dispute_rate": 0.03,
            "product_defect_rate": 0.01,
            "product_return_rate": 0.05,
            "order_value": 50.0,
            "days_since_purchase": 10,
        }

        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Resolution: refund recommended under Section 9.")]
        )

        from agents.resolution_engine import resolution_engine

        state = {
            "case_id": "case_test",
            "customer_id": "cust_001",
            "order_id": "ord_001",
            "dispute_category": "damage",
            "confidence_score": 0.85,
            "evidence_scores": {"doc1": {"damage_score": 0.8, "validity_score": 0.9}},
            "policy_findings": [{"clause": "Section 9", "source": "Consumer Rights Act 2015",
                                  "text": "Quality...", "relevance_score": 0.9}],
            "legal_citations": ["Consumer Rights Act 2015 Section 9"],
            "precedent_cases": [{"case_id": "disp_prev", "similarity": 0.87, "resolution": "refund"}],
            "channel_history": [],
            "graph_subgraph": {"serialised": "Graph context here", "order_value": 50.0},
        }

        result = await resolution_engine(state)
        assert "resolution_recommendation" in result
        assert result["resolution_recommendation"] in ("refund", "replace", "reject", "escalate")
        assert 0.0 <= result["confidence_score"] <= 1.0

def test_extract_features_shape():
    from agents.resolution_engine import _extract_features

    state = {
        "dispute_category": "damage",
        "evidence_scores": {"doc1": {"damage_score": 0.8, "validity_score": 0.9}},
        "policy_findings": [{"relevance_score": 0.85}],
        "precedent_cases": [{"similarity": 0.87}],
    }
    graph_context = {
        "customer_dispute_count": 2,
        "customer_fraud_risk_score": 0.1,
        "seller_refund_rate": 0.05,
        "seller_dispute_rate": 0.04,
        "product_defect_rate": 0.02,
        "product_return_rate": 0.06,
        "order_value": 75.0,
        "days_since_purchase": 15,
    }
    features = _extract_features(state, graph_context)
    assert features.shape == (1, 13)
    assert features.dtype == np.float32

@pytest.mark.asyncio
async def test_human_escalation_first_pass():
    from agents.human_escalation import human_escalation

    state = {
        "case_id": "case_esc",
        "customer_id": "cust_001",
        "order_id": "ord_001",
        "dispute_category": "fraud",
        "confidence_score": 0.45,
        "resolution_recommendation": "escalate",
        "legal_citations": ["Consumer Rights Act 2015 Section 9"],
        "graph_subgraph": {"order_value": 250.0, "resolution_brief": "High-value fraud case."},
        "human_decision": None,
    }

    result = await human_escalation(state)
    assert "graph_subgraph" in result
    assert "escalation_brief" in result["graph_subgraph"]

@pytest.mark.asyncio
async def test_human_escalation_with_decision():
    from agents.human_escalation import human_escalation

    state = {
        "case_id": "case_esc",
        "customer_id": "cust_001",
        "order_id": "ord_001",
        "dispute_category": "fraud",
        "confidence_score": 0.45,
        "resolution_recommendation": "escalate",
        "legal_citations": [],
        "graph_subgraph": {"order_value": 300.0},
        "human_decision": {"resolution": "reject", "notes": "Insufficient evidence"},
    }

    result = await human_escalation(state)
    assert result["resolution_recommendation"] == "reject"
    assert result["confidence_score"] == 1.0
    assert result["requires_human"] is False
    assert result["graph_subgraph"]["human_reviewed"] is True

def test_consumer_rights_act_clauses_loaded():
    from ingestion.policy_ingester import CONSUMER_RIGHTS_ACT_CLAUSES
    assert len(CONSUMER_RIGHTS_ACT_CLAUSES) >= 6
    for clause in CONSUMER_RIGHTS_ACT_CLAUSES:
        assert "act" in clause
        assert "section" in clause
        assert "text" in clause
        assert "Consumer Rights Act 2015" in clause["act"]

def test_deduplicator_roundtrip():
    from ingestion.deduplicator import is_duplicate, mark_ingested

    content = {"test_key": "unique_value_12345_xyz"}
    assert not is_duplicate(content)
    mark_ingested(content)
    assert is_duplicate(content)
