"""Tests for Phase 3 schemas."""
import pytest
from uuid import uuid4
from datetime import datetime, timezone
from app.schemas.claim import ClaimCreate, ClaimType, ClaimStatus, SupportType
from app.schemas.contradiction import ContradictionResponse, ContradictionType, ContradictionSeverity, ResolutionStatus
from app.schemas.source_group import SourceGroupResponse, SourceGroupType

def test_claim_create_schema():
    claim = ClaimCreate(
        content="Test content",
        claim_type=ClaimType.FACT,
        confidence=0.9
    )
    assert claim.content == "Test content"
    assert claim.claim_type == ClaimType.FACT
    assert claim.confidence == 0.9
    assert claim.status == ClaimStatus.UNVERIFIED

def test_contradiction_response_schema():
    now = datetime.now(timezone.utc)
    cont = ContradictionResponse(
        id=uuid4(),
        query_id=uuid4(),
        claim_a_id=uuid4(),
        claim_b_id=uuid4(),
        contradiction_type=ContradictionType.LOGICAL,
        severity=ContradictionSeverity.MEDIUM,
        resolution_status=ResolutionStatus.RESOLVED_A,
        detected_at=now,
        created_at=now,
        updated_at=now
    )
    assert cont.contradiction_type == ContradictionType.LOGICAL
    assert cont.resolution_status == ResolutionStatus.RESOLVED_A

def test_source_group_response_schema():
    now = datetime.now(timezone.utc)
    sg = SourceGroupResponse(
        id=uuid4(),
        query_id=uuid4(),
        name="Group",
        group_type=SourceGroupType.THEMATIC,
        created_at=now,
        updated_at=now
    )
    assert sg.group_type == SourceGroupType.THEMATIC
