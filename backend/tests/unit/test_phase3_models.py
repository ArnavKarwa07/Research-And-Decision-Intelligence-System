"""Tests for Phase 3 models."""
import pytest
from app.models.claim import Claim
from app.models.claim_source import ClaimSource
from app.models.source_group import SourceGroup, SourceGroupMember
from app.models.contradiction import Contradiction
from app.models.source import Source

def test_claim_model_creation():
    claim = Claim(
        content="Test content",
        claim_type="FACT",
        confidence=0.8,
        status="verified"
    )
    assert claim.content == "Test content"
    assert claim.claim_type == "FACT"
    assert claim.confidence == 0.8
    assert claim.status == "verified"

def test_source_model_new_fields():
    source = Source(
        url="http://test.com",
        publisher="Test Pub",
        source_type="academic",
        content_hash="abc123hash",
        independence_group="group1",
        freshness_category="FRESH"
    )
    assert source.publisher == "Test Pub"
    assert source.source_type == "academic"
    assert source.content_hash == "abc123hash"
    assert source.independence_group == "group1"
    assert source.freshness_category == "FRESH"

def test_claim_source_model():
    cs = ClaimSource(
        excerpt="Test excerpt",
        support_type="SUPPORTS",
        relevance_score=0.9
    )
    assert cs.excerpt == "Test excerpt"
    assert cs.support_type == "SUPPORTS"

def test_contradiction_model():
    cont = Contradiction(
        contradiction_type="DIRECT_CONFLICT",
        severity="HIGH",
        resolution_status="unresolved"
    )
    assert cont.contradiction_type == "DIRECT_CONFLICT"
    assert cont.severity == "HIGH"
    assert cont.resolution_status == "unresolved"

def test_source_group_model():
    sg = SourceGroup(
        name="Test Group",
        group_type="INDEPENDENCE"
    )
    assert sg.name == "Test Group"
    assert sg.group_type == "INDEPENDENCE"
