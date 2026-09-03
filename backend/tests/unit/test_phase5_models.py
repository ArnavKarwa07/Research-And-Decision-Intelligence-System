"""Unit tests for Phase 5 SQLAlchemy models (Hypothesis & CritiqueReport)."""
import uuid
import pytest
from app.models.hypothesis import Hypothesis
from app.models.critique_report import CritiqueReport
from app.models.query import Query


def test_hypothesis_model_defaults():
    """Test default values for Hypothesis model."""
    query_id = uuid.uuid4()
    hyp = Hypothesis(
        query_id=query_id,
        statement="Testing quantum acceleration hypothesis"
    )
    
    assert hyp.id is not None
    assert isinstance(hyp.id, uuid.UUID)
    assert hyp.query_id == query_id
    assert hyp.statement == "Testing quantum acceleration hypothesis"
    assert hyp.status == "proposed"
    assert hyp.confidence == 0.5
    assert hyp.supporting_claim_ids == []
    assert hyp.falsifying_claim_ids == []
    assert hyp.evidence_map == []
    assert hyp.falsification_attempts == 0
    assert hyp.max_falsification_attempts == 5


def test_hypothesis_model_custom_values():
    """Test Hypothesis model with explicit custom attributes."""
    hyp_id = uuid.uuid4()
    query_id = uuid.uuid4()
    hyp = Hypothesis(
        id=hyp_id,
        query_id=query_id,
        statement="Alternative hypothesis statement",
        status="supported",
        confidence=0.85,
        supporting_claim_ids=["claim-1", "claim-2"],
        falsifying_claim_ids=["claim-3"],
        evidence_map=[{"evidence_id": "ev-1", "relationship": "supports", "weight": 0.9}],
        falsification_attempts=3,
        max_falsification_attempts=10,
        metadata={"tokens": 300, "cost": 0.002}
    )

    assert hyp.id == hyp_id
    assert hyp.query_id == query_id
    assert hyp.statement == "Alternative hypothesis statement"
    assert hyp.status == "supported"
    assert hyp.confidence == 0.85
    assert len(hyp.supporting_claim_ids) == 2
    assert len(hyp.falsifying_claim_ids) == 1
    assert len(hyp.evidence_map) == 1
    assert hyp.falsification_attempts == 3
    assert hyp.max_falsification_attempts == 10
    assert hyp.metadata_["tokens"] == 300


def test_critique_report_model_defaults():
    """Test default values for CritiqueReport model."""
    query_id = uuid.uuid4()
    report = CritiqueReport(
        query_id=query_id,
        synthesis_snapshot="Initial synthesis text"
    )

    assert report.id is not None
    assert isinstance(report.id, uuid.UUID)
    assert report.query_id == query_id
    assert report.synthesis_snapshot == "Initial synthesis text"
    assert report.findings == []
    assert report.weak_evidence == []
    assert report.missing_variables == []
    assert report.overall_severity == "LOW"
    assert report.recommendations == []
    assert report.replan_triggered is False
    assert report.iteration == 1


def test_critique_report_model_custom_values():
    """Test CritiqueReport model with custom values."""
    report_id = uuid.uuid4()
    query_id = uuid.uuid4()
    report = CritiqueReport(
        id=report_id,
        query_id=query_id,
        synthesis_snapshot="Updated synthesis snapshot",
        findings=["Found confirmation bias in claim 1"],
        weak_evidence=[{"claim_id": "c1", "reason": "SINGLE_SOURCE", "severity": "HIGH"}],
        missing_variables=[{"variable": "market_cost", "impact": "HIGH"}],
        overall_severity="HIGH",
        recommendations=["Gather additional sources"],
        replan_triggered=True,
        iteration=2
    )

    assert report.id == report_id
    assert report.query_id == query_id
    assert len(report.findings) == 1
    assert len(report.weak_evidence) == 1
    assert len(report.missing_variables) == 1
    assert report.overall_severity == "HIGH"
    assert report.replan_triggered is True
    assert report.iteration == 2


def test_query_relationship_collections():
    """Test Query model contains relationship collections for hypotheses and critique_reports."""
    query = Query(text="Sample query")
    assert hasattr(query, "hypotheses")
    assert hasattr(query, "critique_reports")
