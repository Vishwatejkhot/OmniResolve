import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_channel_normaliser_appends_event():
    from agents.channel_normaliser import channel_normaliser

    state = {
        "channel_history": [],
        "customer_id": "",
        "order_id": "",
        "_raw_events": [{
            "channel": "chat",
            "content": "My order ord_abc123 arrived damaged",
            "sender": "user@example.com",
        }],
    }
    result = await channel_normaliser(state)
    assert "channel_history" in result
    assert len(result["channel_history"]) == 1
    assert result["channel_history"][0]["channel"] == "chat"

@pytest.mark.asyncio
async def test_channel_normaliser_strips_card_number():
    from agents.channel_normaliser import channel_normaliser

    state = {
        "channel_history": [],
        "customer_id": "",
        "order_id": "",
        "_raw_events": [{
            "channel": "email",
            "content": "My card 4111 1111 1111 1111 was charged",
            "sender": "test@test.com",
        }],
    }
    result = await channel_normaliser(state)
    content = result["channel_history"][0]["content"]
    assert "4111" not in content
    assert "[CARD_NUMBER]" in content

@pytest.mark.asyncio
async def test_channel_normaliser_extracts_order_id():
    from agents.channel_normaliser import channel_normaliser

    state = {
        "channel_history": [],
        "customer_id": "",
        "order_id": "",
        "_raw_events": [{"channel": "web", "content": "Problem with ord_xf81ab23", "sender": ""}],
    }
    result = await channel_normaliser(state)
    assert result.get("order_id") == "ord_xf81ab23"

@pytest.mark.asyncio
async def test_dispute_classifier_damage():
    with patch("agents.dispute_classifier.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"category": "damage", "confidence": 0.92, "reasoning": "Item arrived broken"}')]
        )

        from agents.dispute_classifier import dispute_classifier

        state = {
            "channel_history": [{"channel": "chat", "content": "Item arrived completely broken"}],
        }
        result = await dispute_classifier(state)
        assert result["dispute_category"] == "damage"
        assert result["confidence_score"] == 0.92

@pytest.mark.asyncio
async def test_dispute_classifier_fraud():
    with patch("agents.dispute_classifier.anthropic.Anthropic") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='{"category": "fraud", "confidence": 0.95, "reasoning": "Unauthorised charge"}')]
        )

        from agents.dispute_classifier import dispute_classifier

        state = {
            "channel_history": [{"channel": "email", "content": "I never made this purchase"}],
        }
        result = await dispute_classifier(state)
        assert result["dispute_category"] == "fraud"

@pytest.mark.asyncio
async def test_customer_resolver_finds_by_email():
    with patch("agents.customer_resolver.run_query", new_callable=AsyncMock) as mock_q:
        mock_q.return_value = [{"c": {"id": "cust_0042", "name": "Bob"}}]

        from agents.customer_resolver import customer_resolver

        state = {
            "customer_id": "",
            "order_id": "",
            "channel_history": [{"sender": "bob@example.com", "content": "", "raw_channel_id": ""}],
        }
        result = await customer_resolver(state)
        assert result["customer_id"] == "cust_0042"

@pytest.mark.asyncio
async def test_customer_resolver_guest_fallback():
    with patch("agents.customer_resolver.run_query", new_callable=AsyncMock) as mock_q:
        mock_q.return_value = []

        from agents.customer_resolver import customer_resolver

        state = {
            "customer_id": "",
            "order_id": "",
            "channel_history": [{"sender": "new@example.com", "content": "", "raw_channel_id": ""}],
        }
        result = await customer_resolver(state)
        assert result.get("customer_id", "").startswith("cust_")

@pytest.mark.asyncio
async def test_evidence_analyser_no_docs():
    from agents.evidence_analyser import evidence_analyser

    state = {"documents": [], "case_id": "test", "dispute_category": "damage"}
    result = await evidence_analyser(state)
    assert result == {"evidence_scores": {}}

@pytest.mark.asyncio
async def test_evidence_analyser_no_image_docs():
    from agents.evidence_analyser import evidence_analyser

    state = {
        "documents": [{"type": "document", "url": "file.txt", "id": "doc1"}],
        "case_id": "test",
        "dispute_category": "damage",
    }
    result = await evidence_analyser(state)
    assert result == {"evidence_scores": {}}
