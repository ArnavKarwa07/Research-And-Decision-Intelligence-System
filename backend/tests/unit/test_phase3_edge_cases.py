import pytest
from datetime import datetime, timezone, timedelta
from app.services.source_scorer import SourceScorer
from app.services.confidence_engine import ConfidenceEngine
from app.models.source import Source

def test_confidence_engine_none_claim_type():
    # Bug: None claim_type causes AttributeError: 'NoneType' object has no attribute 'upper'
    result = ConfidenceEngine.calculate(
        claim_type=None,
        source_credibility_avg=0.8
    )
    assert result > 0.0

def test_source_scorer_freshness_future_date():
    # Bug: A future date yields negative days_old, which incorrectly falls under "FRESH"
    now = datetime.now(timezone.utc)
    future_date = now + timedelta(days=365)
    
    result = SourceScorer.classify_freshness(future_date, "medium")
    assert result == "FRESH", "Future date should clamp to 0 days old, which is FRESH."

def test_source_scorer_independence_none_url():
    s = Source(url=None, content_hash=None)
    result = SourceScorer.classify_independence_groups([s])
    assert "unknown" in result
