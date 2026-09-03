import uuid
from app.models.claim import Claim
from app.models.claim_source import ClaimSource
from app.models.source_group import SourceGroup, SourceGroupMember
from app.models.contradiction import Contradiction
from app.models.source import Source

def test_claim_model_creation():
    qid = uuid.uuid4()
    claim = Claim(
        query_id=qid,
        content="Test content",
        claim_type="FACT",
        confidence=0.8,
        status="verified"
    )
    assert claim.query_id == qid
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
    cid = uuid.uuid4()
    sid = uuid.uuid4()
    cs = ClaimSource(
        claim_id=cid,
        source_id=sid,
        excerpt="Test excerpt",
        support_type="SUPPORTS",
        relevance_score=0.9
    )
    assert cs.claim_id == cid
    assert cs.source_id == sid
    assert cs.excerpt == "Test excerpt"
    assert cs.support_type == "SUPPORTS"

def test_contradiction_model():
    qid = uuid.uuid4()
    ca_id = uuid.uuid4()
    cb_id = uuid.uuid4()
    cont = Contradiction(
        query_id=qid,
        claim_a_id=ca_id,
        claim_b_id=cb_id,
        contradiction_type="DIRECT_CONFLICT",
        severity="HIGH",
        resolution_status="unresolved"
    )
    assert cont.query_id == qid
    assert cont.claim_a_id == ca_id
    assert cont.claim_b_id == cb_id
    assert cont.contradiction_type == "DIRECT_CONFLICT"
    assert cont.severity == "HIGH"
    assert cont.resolution_status == "unresolved"

def test_source_group_model():
    qid = uuid.uuid4()
    sg = SourceGroup(
        query_id=qid,
        name="Test Group",
        group_type="INDEPENDENCE"
    )
    assert sg.query_id == qid
    assert sg.name == "Test Group"
    assert sg.group_type == "INDEPENDENCE"

