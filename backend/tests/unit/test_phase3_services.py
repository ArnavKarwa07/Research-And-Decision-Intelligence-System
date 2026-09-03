"""Tests for Phase 3 services."""
import pytest
from datetime import datetime, timezone, timedelta
from app.services.source_scorer import SourceScorer
from app.services.confidence_engine import ConfidenceEngine
from app.models.source import Source

def test_source_scorer_credibility():
    score = SourceScorer.calculate_credibility(
        domain_authority=0.8,
        source_type="academic",
        recency_days=10.0,
        cross_ref_count=2,
        is_independent=True
    )
    # 0.8 * 1.2 = 0.96
    # + (2*0.05) = 1.06
    # * 1.1 = 1.166 -> capped at 1.0
    assert score == 1.0

def test_source_scorer_freshness():
    now = datetime.now(timezone.utc)
    fresh_date = now - timedelta(days=10)
    assert SourceScorer.classify_freshness(fresh_date, "medium") == "FRESH"
    
    stale_date = now - timedelta(days=400)
    assert SourceScorer.classify_freshness(stale_date, "medium") == "STALE"

def test_source_scorer_independence():
    s1 = Source(url="http://test.com/a", content_hash="hash1")
    s2 = Source(url="http://test.com/b", content_hash="hash2")
    s3 = Source(url="http://other.com/c", content_hash="hash1")
    
    groups = SourceScorer.classify_independence_groups([s1, s2, s3])
    assert len(groups) == 2
    assert len(groups["hash_hash1"]) == 2
    assert len(groups["hash_hash2"]) == 1

def test_confidence_engine():
    conf = ConfidenceEngine.calculate(
        claim_type="FACT",
        source_credibility_avg=0.8,
        independence_factor=1.2,
        recency_factor=1.0,
        verification_bonus=1.1
    )
    # 0.9 * 0.8 * 1.2 * 1.0 * 1.1 = 0.9504
    assert 0.9 < conf < 1.0
    
    conf2 = ConfidenceEngine.calculate(
        claim_type="OPINION",
        source_credibility_avg=0.5
    )
    # 0.2 * 0.5 = 0.1
    assert conf2 == 0.1
