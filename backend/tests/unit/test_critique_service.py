"""Unit tests for CritiqueService (P5-17)."""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.query import Query
from app.models.critique_report import CritiqueReport
from app.services.critique_service import CritiqueService, critique_service
from app.config import settings


def test_should_trigger_replan_severity_levels():
    """Test should_trigger_replan decision logic across severity levels and conditions."""
    service = CritiqueService()

    # 1. LOW severity -> False
    report_low = {"overall_severity": "LOW", "weak_evidence": [], "replan_recommended": False}
    assert service.should_trigger_replan(report_low, settings) is False

    # 2. MEDIUM severity -> False
    report_med = {"overall_severity": "MEDIUM", "weak_evidence": [], "replan_recommended": False}
    assert service.should_trigger_replan(report_med, settings) is False

    # 3. HIGH severity -> True (matches default threshold HIGH)
    report_high = {"overall_severity": "HIGH", "weak_evidence": [], "replan_recommended": False}
    assert service.should_trigger_replan(report_high, settings) is True

    # 4. CRITICAL severity -> True
    report_crit = {"overall_severity": "CRITICAL", "weak_evidence": [], "replan_recommended": False}
    assert service.should_trigger_replan(report_crit, settings) is True

    # 5. Critical weak evidence item present -> True even if overall severity is LOW
    report_weak_crit = {
        "overall_severity": "LOW",
        "weak_evidence": [{"claim_id": "c1", "severity": "CRITICAL"}],
        "replan_recommended": False
    }
    assert service.should_trigger_replan(report_weak_crit, settings) is True

    # 6. Explicit replan_recommended flag -> True
    report_rec = {"overall_severity": "LOW", "weak_evidence": [], "replan_recommended": True}
    assert service.should_trigger_replan(report_rec, settings) is True


@pytest.mark.asyncio
async def test_run_critique_nonexistent_query():
    """Test run_critique raises ValueError when query_id is not found."""
    service = CritiqueService()
    mock_db = AsyncMock(spec=AsyncSession)

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_res

    with pytest.raises(ValueError, match="not found"):
        await service.run_critique(mock_db, uuid.uuid4())


@pytest.mark.asyncio
async def test_run_critique_execution_and_persistence():
    """Test successful run_critique flow and DB persistence."""
    service = CritiqueService()
    query_id = uuid.uuid4()
    query = Query(id=query_id, text="Evaluating system safety", summary="Initial synthesis")

    mock_db = AsyncMock(spec=AsyncSession)
    
    # Mock query lookup
    q_res = MagicMock()
    q_res.scalar_one_or_none.return_value = query

    # Mock claims & evidence empty list lookups
    claims_res = MagicMock()
    claims_res.scalars.return_value.all.return_value = []

    ev_res = MagicMock()
    ev_res.scalars.return_value.all.return_value = []

    # Mock iteration count lookup
    count_res = MagicMock()
    count_res.scalar.return_value = 1  # 1 existing report -> iteration 2

    mock_db.execute.side_effect = [q_res, claims_res, ev_res, count_res]

    report = await service.run_critique(mock_db, query_id)

    assert report.query_id == query_id
    assert report.iteration == 2
    assert mock_db.add.called
    assert mock_db.commit.called
