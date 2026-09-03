import pytest
import uuid
from typing import List
from datetime import datetime

from app.agents.agent_contracts import (
    AtomicClaim, ClaimType, EvidenceSupportStatus, SourceMetadata
)
from app.agents.base import AgentConfig
from app.agents.contradiction import ContradictionAgent

@pytest.fixture
def agent():
    config = AgentConfig(max_steps=5, max_tokens=1000, timeout_seconds=30, allowed_tools=[])
    return ContradictionAgent(config)

def create_claim(text: str, source_url: str = "http://example.com", cid: str = None) -> AtomicClaim:
    return AtomicClaim(
        id=cid or f"claim-{uuid.uuid4().hex[:8]}",
        text=text,
        claim_type=ClaimType.FACT,
        confidence=0.9,
        support_status=EvidenceSupportStatus.SUPPORTED,
        source_url=source_url,
        source_title="Example",
        excerpt="Example excerpt"
    )

def test_semantic_similarity(agent):
    c1 = create_claim("The quick brown fox jumps over the lazy dog.")
    c2 = create_claim("The quick brown fox jumps over the lazy dog often.")
    c3 = create_claim("Completely unrelated text without overlap.")
    
    matches = agent.check_semantic_similarity([c1, c2, c3])
    assert len(matches) == 1
    assert matches[0] == (c1, c2)

def test_direct_contradiction(agent):
    c1 = create_claim("The sky is blue and this is true.")
    c2 = create_claim("The sky is blue and this is false.")
    assert agent.check_direct_contradiction(c1, c2) is True
    
    c3 = create_claim("Prices will increase next year.")
    c4 = create_claim("Prices will decrease next year.")
    assert agent.check_direct_contradiction(c3, c4) is True

def test_statistical_consistency(agent):
    c1 = create_claim("The revenue is 100.0 million.", "http://example.com/1")
    c2 = create_claim("The revenue is 150.0 million.", "http://example.com/2")
    
    matches = agent.check_statistical_consistency([c1, c2])
    assert len(matches) == 1

def test_statistical_consistency_edge_case(agent):
    c1 = create_claim("The revenue is 100.0 million.", "http://example.com/1")
    c2 = create_claim("The revenue is 0.0 million.", "http://example.com/2")
    
    matches = agent.check_statistical_consistency([c1, c2])
    assert len(matches) == 1, "Should catch contradiction when second value is 0"
    
    matches2 = agent.check_statistical_consistency([c2, c1])
    assert len(matches2) == 1, "Should catch contradiction when first value is 0"

def test_temporal_consistency(agent):
    c1 = create_claim("The CEO is John in 2023.", "http://example.com/1")
    c2 = create_claim("The CEO is Jane in 2024.", "http://example.com/2")
    
    matches = agent.check_temporal_consistency([c1, c2])
    assert len(matches) == 1

def test_methodological_consistency(agent):
    c1 = create_claim("A survey shows people like apples.", "http://example.com/1")
    c2 = create_claim("An rct shows people like apples.", "http://example.com/2")
    
    matches = agent.check_methodological_consistency([c1, c2])
    assert len(matches) == 1

def test_severity_classification(agent):
    assert agent.assign_severity("DIRECT_CONFLICT") == "critical"
    assert agent.assign_severity("NUMERIC_MISMATCH") == "high"
    assert agent.assign_severity("DATE_MISMATCH") == "medium"
    assert agent.assign_severity("METHODOLOGICAL") == "low"

def test_auto_resolution_credibility(agent):
    c1 = create_claim("A", "http://high.com", "c1")
    c2 = create_claim("B", "http://low.com", "c2")
    
    sources = [
        SourceMetadata(url="http://high.com", title="High", quality_score="HIGH"),
        SourceMetadata(url="http://low.com", title="Low", quality_score="LOW")
    ]
    
    status, notes, winner_id = agent.apply_resolution_strategies(c1, c2, sources)
    assert status == "resolved"
    assert winner_id == "c1"

def test_auto_resolution_recency(agent):
    c1 = create_claim("A", "http://old.com", "c1")
    c2 = create_claim("B", "http://new.com", "c2")
    
    sources = [
        SourceMetadata(url="http://old.com", title="Old", quality_score="MEDIUM", retrieved_at="2024-01-01T00:00:00Z"),
        SourceMetadata(url="http://new.com", title="New", quality_score="MEDIUM", retrieved_at="2024-02-01T00:00:00Z")
    ]
    
    status, notes, winner_id = agent.apply_resolution_strategies(c1, c2, sources)
    assert status == "resolved"
    assert winner_id == "c2"

def test_escalation_state(agent):
    c1 = create_claim("A", "http://same.com/1", "c1")
    c2 = create_claim("B", "http://same.com/2", "c2")
    
    sources = [
        SourceMetadata(url="http://same.com/1", title="Same 1", quality_score="MEDIUM", retrieved_at="2024-01-01T00:00:00Z"),
        SourceMetadata(url="http://same.com/2", title="Same 2", quality_score="MEDIUM", retrieved_at="2024-01-01T00:00:00Z")
    ]
    
    status, notes, winner_id = agent.apply_resolution_strategies(c1, c2, sources)
    assert status == "escalated"
    assert winner_id is None

@pytest.mark.asyncio
async def test_agent_step(agent):
    c1 = create_claim("The revenue is 100.0 million.", "http://same.com/1", "c1")
    c2 = create_claim("The revenue is 150.0 million.", "http://same.com/2", "c2")
    
    sources = [
        SourceMetadata(url="http://same.com/1", title="Same 1", quality_score="MEDIUM", retrieved_at="2024-01-01T00:00:00Z"),
        SourceMetadata(url="http://same.com/2", title="Same 2", quality_score="MEDIUM", retrieved_at="2024-01-01T00:00:00Z")
    ]
    
    input_data = {
        "claims": [c1, c2],
        "sources": sources,
        "query_id": "test-query"
    }
    
    result = await agent.step(input_data)
    assert not result.should_continue
    
    output = await agent.compile_output()
    assert output["escalated_count"] == 1
    assert output["auto_resolved_count"] == 0
    assert len(output["contradictions"]) == 1
    assert output["contradictions"][0]["contradiction_type"] == "NUMERIC_MISMATCH"
