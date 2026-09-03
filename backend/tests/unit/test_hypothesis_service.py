"""Unit tests for HypothesisService (P5-17)."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.hypothesis import Hypothesis
from app.models.query import Query
from app.services.hypothesis_service import HypothesisService, hypothesis_service


def test_recalculate_confidence_pure_math():
    """Test recalculate_confidence mathematical formula and boundary edge cases."""
    service = HypothesisService()

    # 1. Empty map -> returns 0.5
    assert service.recalculate_confidence([]) == 0.5

    # 2. Only supporting evidence -> normalized to 1.0
    sup_map = [
        {"relationship": "supports", "weight": 1.0},
        {"relationship": "supporting", "weight": 0.5}
    ]
    assert service.recalculate_confidence(sup_map) == 1.0

    # 3. Only falsifying evidence -> normalized to 0.0
    fals_map = [
        {"relationship": "falsifies", "weight": 1.0}
    ]
    assert service.recalculate_confidence(fals_map) == 0.0

    # 4. Balanced evidence -> (1.0 - 1.0)/2.0 normalized to 0.5
    bal_map = [
        {"relationship": "supports", "weight": 1.0},
        {"relationship": "falsifies", "weight": 1.0}
    ]
    assert service.recalculate_confidence(bal_map) == 0.5

    # 5. Net positive -> (1.5 - 0.5)/2.0 = 1.0 / 2.0 = 0.5 net ratio -> (0.5+1)/2 = 0.75
    net_pos = [
        {"relationship": "supports", "weight": 1.5},
        {"relationship": "falsifies", "weight": 0.5}
    ]
    assert service.recalculate_confidence(net_pos) == 0.75

    # 6. Total weight 0 -> returns 0.5
    zero_map = [{"relationship": "neutral", "weight": 0.0}]
    assert service.recalculate_confidence(zero_map) == 0.5

    # 7. Safe handling of invalid weight inputs (None, string, negative)
    invalid_map = [
        {"relationship": "supports", "weight": None},
        {"relationship": "supports", "weight": "invalid"},
        {"relationship": "falsifies", "weight": -5.0}
    ]
    # None -> 1.0, "invalid" -> 1.0, -5.0 -> 0.0 => total sup=2.0, fals=0.0 => 1.0
    assert service.recalculate_confidence(invalid_map) == 1.0


@pytest.mark.asyncio
async def test_hypothesis_service_generate_hypotheses():
    """Test generating hypotheses for a query using AsyncSession mock."""
    service = HypothesisService()
    query_id = uuid.uuid4()

    mock_db = AsyncMock(spec=AsyncSession)
    mock_query = Query(id=query_id, text="How to scale vector databases?")
    
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_query
    mock_db.execute.return_value = mock_result

    hypotheses = await service.generate_hypotheses(mock_db, query_id)

    assert len(hypotheses) >= 3
    assert mock_db.add.call_count >= 3
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_hypothesis_service_map_evidence():
    """Test mapping evidence entry to a hypothesis and recalculating confidence."""
    service = HypothesisService()
    hyp_id = uuid.uuid4()
    query_id = uuid.uuid4()

    hyp = Hypothesis(
        id=hyp_id,
        query_id=query_id,
        statement="Initial hypothesis",
        confidence=0.5,
        evidence_map=[],
        supporting_claim_ids=[],
        falsifying_claim_ids=[]
    )

    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = hyp
    mock_db.execute.return_value = mock_result

    evidence_entry = {
        "claim_id": "c-100",
        "relationship": "supports",
        "weight": 1.0,
        "justification": "Primary benchmark data"
    }

    updated_hyp = await service.map_evidence(mock_db, hyp_id, evidence_entry)

    assert len(updated_hyp.evidence_map) == 1
    assert "c-100" in updated_hyp.supporting_claim_ids
    assert updated_hyp.confidence == 1.0
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_hypothesis_service_run_falsification_attempts_cap():
    """Test run_falsification stops when max_falsification_attempts is reached."""
    service = HypothesisService()
    hyp_id = uuid.uuid4()

    hyp = Hypothesis(
        id=hyp_id,
        query_id=uuid.uuid4(),
        statement="Capped hypothesis",
        confidence=0.5,
        falsification_attempts=5,
        max_falsification_attempts=5
    )

    mock_db = AsyncMock(spec=AsyncSession)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = hyp
    mock_db.execute.return_value = mock_result

    res = await service.run_falsification(mock_db, hyp_id)

    assert "reached" in res["message"]
    assert res["falsification_attempts"] == 5
