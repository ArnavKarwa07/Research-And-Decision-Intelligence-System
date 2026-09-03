"""Unit tests for Phase 5 Pydantic schemas."""
import uuid
from datetime import datetime
import pytest
from pydantic import ValidationError

from app.schemas.hypothesis import (
    HypothesisStatus, EvidenceRelationship, CritiqueSeverity, WeakEvidenceReason,
    EvidenceMapEntry, WeakEvidenceItem, MissingVariableItem,
    HypothesisCreate, HypothesisUpdate, HypothesisResponse, HypothesisListResponse,
    CritiqueReportResponse, CritiqueReportListResponse,
    SelfChallengeRequest, SelfChallengeResponse
)


def test_enum_case_insensitivity():
    """Test Enum parsing case insensitivity for Phase 5 schemas."""
    assert HypothesisStatus("proposed") == HypothesisStatus.PROPOSED
    assert HypothesisStatus("SUPPORTED") == HypothesisStatus.SUPPORTED

    assert EvidenceRelationship("supports") == EvidenceRelationship.SUPPORTS
    assert EvidenceRelationship("FALSIFIES") == EvidenceRelationship.FALSIFIES

    assert CritiqueSeverity("high") == CritiqueSeverity.HIGH
    assert CritiqueSeverity("CRITICAL") == CritiqueSeverity.CRITICAL

    assert WeakEvidenceReason("single_source") == WeakEvidenceReason.SINGLE_SOURCE
    assert WeakEvidenceReason("LOW_CONFIDENCE") == WeakEvidenceReason.LOW_CONFIDENCE


def test_evidence_map_entry_validation():
    """Test EvidenceMapEntry validation and weight bounds."""
    entry = EvidenceMapEntry(
        evidence_id="ev-123",
        relationship=EvidenceRelationship.SUPPORTS,
        weight=0.8,
        justification="Strong alignment"
    )
    assert entry.evidence_id == "ev-123"
    assert entry.weight == 0.8

    # Invalid weight > 1.0
    with pytest.raises(ValidationError):
        EvidenceMapEntry(evidence_id="ev-1", relationship=EvidenceRelationship.SUPPORTS, weight=1.5)

    # Invalid weight < 0.0
    with pytest.raises(ValidationError):
        EvidenceMapEntry(evidence_id="ev-1", relationship=EvidenceRelationship.SUPPORTS, weight=-0.1)


def test_hypothesis_create_schema():
    """Test HypothesisCreate schema validation and defaults."""
    create_schema = HypothesisCreate(statement="Hypothesis statement text")
    assert create_schema.statement == "Hypothesis statement text"
    assert create_schema.status == HypothesisStatus.PROPOSED
    assert create_schema.confidence == 0.5
    assert create_schema.max_falsification_attempts == 5

    # Out of range confidence validation
    with pytest.raises(ValidationError):
        HypothesisCreate(statement="Invalid", confidence=1.2)


def test_hypothesis_response_schema():
    """Test HypothesisResponse model dump and serialization."""
    hyp_id = uuid.uuid4()
    query_id = uuid.uuid4()
    now = datetime.now()

    response = HypothesisResponse(
        id=hyp_id,
        query_id=query_id,
        statement="Response statement",
        status=HypothesisStatus.ACTIVE,
        confidence=0.75,
        supporting_claim_ids=["c1"],
        falsifying_claim_ids=[],
        evidence_map=[
            EvidenceMapEntry(
                evidence_id="e1",
                relationship=EvidenceRelationship.SUPPORTS,
                weight=0.9
            )
        ],
        falsification_attempts=1,
        max_falsification_attempts=5,
        created_at=now,
        updated_at=now
    )

    dumped = response.model_dump()
    assert dumped["id"] == hyp_id
    assert dumped["status"] == HypothesisStatus.ACTIVE
    assert len(dumped["evidence_map"]) == 1


def test_critique_report_response_schema():
    """Test CritiqueReportResponse schema."""
    report_id = uuid.uuid4()
    query_id = uuid.uuid4()

    response = CritiqueReportResponse(
        id=report_id,
        query_id=query_id,
        synthesis_snapshot="Test snapshot",
        findings=["Finding 1"],
        weak_evidence=[
            WeakEvidenceItem(
                claim_id="c1",
                reason=WeakEvidenceReason.SINGLE_SOURCE,
                severity=CritiqueSeverity.HIGH,
                details="Single source dependency",
                remediation="Add sources"
            )
        ],
        missing_variables=[
            MissingVariableItem(
                variable="cost",
                impact="HIGH",
                category="OMITTED_FACTOR",
                suggested_action="Add cost analysis"
            )
        ],
        overall_severity=CritiqueSeverity.HIGH,
        recommendations=["Action item 1"],
        replan_triggered=True,
        iteration=1,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )

    assert response.overall_severity == CritiqueSeverity.HIGH
    assert response.replan_triggered is True
    assert len(response.weak_evidence) == 1


def test_self_challenge_request_response_schemas():
    """Test SelfChallengeRequest and SelfChallengeResponse schemas."""
    query_id = uuid.uuid4()
    req = SelfChallengeRequest(query_id=query_id)
    assert req.max_iterations == 3
    assert req.confidence_threshold == 0.3

    res = SelfChallengeResponse(
        query_id=query_id,
        hypotheses=[],
        critique_reports=[],
        replan_count=1,
        final_status="passed_cleanly"
    )
    assert res.replan_count == 1
    assert res.final_status == "passed_cleanly"
