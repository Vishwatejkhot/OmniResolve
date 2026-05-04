import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from graphrag.rrf_fusion import RankedResult, reciprocal_rank_fusion
from graphrag.graph_serialiser import serialise_subgraph, serialise_case_context

def test_rrf_single_list():
    results = [
        RankedResult("a", "Dispute", {"id": "a"}, 0.9),
        RankedResult("b", "Dispute", {"id": "b"}, 0.8),
        RankedResult("c", "Dispute", {"id": "c"}, 0.7),
    ]
    fused = reciprocal_rank_fusion(results)
    assert [r.node_id for r in fused] == ["a", "b", "c"]

def test_rrf_two_lists_boost_overlap():
    list1 = [RankedResult("x", "Dispute", {}, 0.9), RankedResult("y", "Dispute", {}, 0.8)]
    list2 = [RankedResult("y", "Dispute", {}, 0.95), RankedResult("z", "Dispute", {}, 0.7)]
    fused = reciprocal_rank_fusion(list1, list2)
    node_ids = [r.node_id for r in fused]
    assert node_ids[0] == "y"

def test_rrf_empty_lists():
    fused = reciprocal_rank_fusion([], [])
    assert fused == []

def test_rrf_scores_positive():
    results = [RankedResult(str(i), "T", {}) for i in range(10)]
    fused = reciprocal_rank_fusion(results)
    for r in fused:
        assert r.score > 0

def test_serialise_subgraph_contains_nodes():
    results = [
        RankedResult("d1", "Dispute", {"id": "d1", "category": "damage", "resolution": "refund"}, 0.9),
        RankedResult("p1", "Policy", {"id": "p1", "clause": "Section 9", "source": "Consumer Rights Act 2015"}, 0.8),
    ]
    output = serialise_subgraph(results)
    assert "GRAPH CONTEXT" in output
    assert "DISPUTE" in output
    assert "POLICY" in output
    assert "d1" in output

def test_serialise_subgraph_max_nodes():
    results = [RankedResult(str(i), "Dispute", {"id": str(i)}) for i in range(30)]
    output = serialise_subgraph(results, max_nodes=5)
    assert output.count("[DISPUTE]") == 5

def test_serialise_case_context():
    output = serialise_case_context(
        customer={"id": "c1", "name": "Alice", "dispute_count": 2, "fraud_risk_score": 0.1},
        order={"id": "ord_001", "total_value": 99.99, "status": "delivered", "channel": "web", "date": "2025-01-01"},
        product={"sku": "SKU-1234", "name": "Headphones", "category": "electronics", "defect_rate": 0.01, "return_rate": 0.05},
        seller={"id": "s1", "name": "TechSeller", "dispute_rate": 0.04, "refund_rate": 0.08, "fraud_signals": 0},
        disputes=[],
        policy_findings=[{"clause": "Section 9", "source": "Consumer Rights Act 2015", "text": "Satisfactory quality...", "relevance_score": 0.95}],
        precedents=[{"case_id": "disp_abc", "similarity": 0.87, "resolution": "refund"}],
    )
    assert "Alice" in output
    assert "Section 9" in output
    assert "disp_abc" in output
    assert "Consumer Rights Act 2015" in output

@pytest.mark.asyncio
async def test_run_query_returns_list():
    with patch("graphrag.neo4j_client._get_driver") as mock_driver:
        mock_session = AsyncMock()
        mock_result = AsyncMock()
        mock_result.__aiter__ = MagicMock(return_value=iter([]))
        mock_session.run.return_value = mock_result
        mock_driver.return_value.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.return_value.session.return_value.__aexit__ = AsyncMock(return_value=False)

        from graphrag.neo4j_client import run_query
        result = await run_query("RETURN 1", {})
        assert isinstance(result, list)
