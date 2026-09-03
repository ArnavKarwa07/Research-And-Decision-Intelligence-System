"""Unit tests for SelfChallengeService (P5-17)."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query import Query
from app.models.hypothesis import Hypothesis
from app.services.self_challenge_service import SelfChallengeService


@pytest.mark.asyncio
async def test_self_challenge_service_initialization():
    """Test SelfChallengeService configuration defaults."""
    service = SelfChallengeService()
    assert service.max_replan_iterations == 3
    assert service.confidence_threshold == 0.3
    assert service.severity_threshold == "HIGH"


@pytest.mark.asyncio
async def test_get_or_create_query_hypotheses_fallback():
    """Test generating 3 default competing hypotheses when DB is absent or empty."""
    service = SelfChallengeService(db=None)
    query_id = uuid.uuid4()
    query_text = "What is the optimal database architecture for graph data?"

    hypotheses = await service._get_or_create_query_hypotheses(query_id, query_text)

    assert len(hypotheses) == 3
    statements = [h["statement"] for h in hypotheses]
    assert any("Primary hypothesis" in s for s in statements)
    assert any("Alternative hypothesis A" in s for s in statements)
    assert any("Alternative hypothesis B" in s for s in statements)


@pytest.mark.asyncio
async def test_run_self_challenge_clean_pass():
    """Test self-challenge pipeline completing cleanly without replan when audit passes."""
    service = SelfChallengeService(db=None)
    query_id = uuid.uuid4()

    # Mock falsification pass to return high confidence supported hypotheses
    with patch.object(service, "run_falsification_pass", new_callable=AsyncMock) as mock_falsify:
        mock_falsify.return_value = [
            {"id": "h1", "statement": "Hyp 1", "status": "supported", "confidence": 0.85},
            {"id": "h2", "statement": "Hyp 2", "status": "supported", "confidence": 0.80},
            {"id": "h3", "statement": "Hyp 3", "status": "inconclusive", "confidence": 0.60}
        ]

        res = await service.run_self_challenge(query_id)

        assert res["final_status"] == "passed_cleanly"
        assert res["replan_count"] == 0
        assert res["finalized_with_caveats"] is False
        assert len(res["critique_reports"]) == 1


@pytest.mark.asyncio
async def test_run_self_challenge_circuit_breaker():
    """Test circuit breaker trips after max_replan_iterations (3) when severity remains HIGH."""
    service = SelfChallengeService(db=None)
    query_id = uuid.uuid4()

    # Mock falsification pass to return low confidence / falsified hypotheses
    with patch.object(service, "run_falsification_pass", new_callable=AsyncMock) as mock_falsify:
        mock_falsify.return_value = [
            {"id": "h1", "statement": "Hyp 1", "status": "falsified", "confidence": 0.15},
            {"id": "h2", "statement": "Hyp 2", "status": "falsified", "confidence": 0.10},
            {"id": "h3", "statement": "Hyp 3", "status": "falsified", "confidence": 0.20}
        ]

        res = await service.run_self_challenge(query_id)

        assert res["final_status"] == "finalized_with_caveats"
        assert res["replan_count"] == 3  # Max replan iterations
        assert res["finalized_with_caveats"] is True
        assert len(res["critique_reports"]) == 4  # Initial pass + 3 replan passes
