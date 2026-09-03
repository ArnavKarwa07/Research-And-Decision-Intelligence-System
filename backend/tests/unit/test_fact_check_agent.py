import pytest
import uuid
import os
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

os.environ["LLM_PROVIDER"] = "mock"
from app.services.claim_extractor import ClaimExtractor
from app.agents.fact_check import FactCheckAgent
from app.agents.agent_contracts import FactCheckInput, AtomicClaim, ClaimType, EvidenceSupportStatus, SourceMetadata
from app.models.claim import Claim
from app.agents.base import AgentStatus

pytestmark = pytest.mark.asyncio

@pytest.fixture
def mock_db_session():
    session = AsyncMock(spec=AsyncSession)
    return session

async def test_claim_extractor_extract_claims(mock_db_session):
    extractor = ClaimExtractor(db_session=mock_db_session)
    # mock LLM
    mock_llm = AsyncMock()
    mock_result = MagicMock()
    mock_result.claims = [
        MagicMock(text="The sky is blue", claim_type=MagicMock(value="FACT")),
        MagicMock(text="I think it will rain", claim_type=MagicMock(value="PREDICTION")),
    ]
    mock_llm.generate_structured.return_value = mock_result
    extractor.llm = mock_llm
    
    query_id = uuid.uuid4()
    claims = await extractor.extract_claims("The sky is blue and I think it will rain.", query_id)
    
    assert len(claims) == 2
    assert claims[0].content == "The sky is blue"
    assert claims[0].claim_type == "FACT"
    assert claims[1].content == "I think it will rain"
    assert claims[1].claim_type == "PREDICTION"
    assert mock_db_session.add.call_count == 2
    mock_db_session.commit.assert_called_once()

async def test_claim_extractor_link_provenance(mock_db_session):
    extractor = ClaimExtractor(db_session=mock_db_session)
    claim = Claim(id=uuid.uuid4(), content="The sky is blue")
    
    source_snippets = [
        {"source_id": str(uuid.uuid4()), "content": "Today, The sky is blue and clear."},
        {"source_id": str(uuid.uuid4()), "content": "Irrelevant text"}
    ]
    
    links = await extractor.link_provenance(claim, source_snippets)
    assert len(links) == 1
    assert links[0].excerpt == "The sky is blue"
    assert links[0].excerpt_location["startChar"] == 7
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

async def test_fact_check_agent_search_strategies_and_deduplication():
    agent = FactCheckAgent()
    mock_tool_registry = AsyncMock()
    
    # We will mock the tools
    async def mock_call(tool_name, input_data, agent_id):
        if tool_name == "web_search":
            query = input_data["query"]
            if "site:.gov" in query:
                return MagicMock(success=True, data=[{"url": "http://gov.org", "title": "Gov Site"}])
            elif "fake" in query:
                return MagicMock(success=True, data=[{"url": "http://debunk.com", "title": "Debunk"}])
            else:
                return MagicMock(success=True, data=[{"url": "http://direct.com", "title": "Direct"}, {"url": "http://existing.com", "title": "Exist"}])
        elif tool_name == "extract_content":
            url = input_data["url"]
            if url == "http://direct.com":
                return MagicMock(success=True, data=MagicMock(text="The sky is indeed blue."))
            elif url == "http://gov.org":
                return MagicMock(success=True, data=MagicMock(text="The sky is indeed blue.")) # duplicate content!
            elif url == "http://debunk.com":
                return MagicMock(success=True, data=MagicMock(text="Some say the sky is blue."))
    
    mock_tool_registry.call.side_effect = mock_call
    agent.set_tool_registry(mock_tool_registry)
    
    # Mock LLM provider for planning and analysis
    mock_llm = AsyncMock()
    
    # First LLM call is planning (SearchStrategyResult)
    mock_plan = MagicMock()
    mock_plan.queries = ["sky is blue", "sky is blue site:.gov", "sky is blue fake"]
    
    # Second, third, fourth LLM calls are VerdictResult
    # 1. direct.com -> supports
    mock_verdict_1 = MagicMock(verdict="verified", confidence_adjustment=1.2)
    # 2. debunk.com -> refuted
    mock_verdict_2 = MagicMock(verdict="refuted", confidence_adjustment=0.5)
    
    mock_llm.generate_structured.side_effect = [mock_plan, mock_verdict_1, mock_verdict_2]
    agent.set_llm_provider(mock_llm)
    
    claim = AtomicClaim(id="1", text="sky is blue", claim_type=ClaimType.FACT, confidence=0.5, support_status=EvidenceSupportStatus.UNSUPPORTED)
    
    input_data = {
        "claim": claim.model_dump(),
        "existing_source_urls": ["http://existing.com"]
    }
    
    output = await agent.run(input_data)
    
    assert agent.state.status == AgentStatus.COMPLETED
    
    # Check deduplication: existing.com should be skipped.
    assert "http://existing.com" not in [s["url"] for s in agent.internal_state["search_results"]]
    
    # Check deduplication: gov.org has same content as direct.com (duplicate hash), should be skipped during extraction
    assert len(agent.internal_state["extracted_contents"]) == 0 # because they are popped during analysis
    # Let's check the outputs
    
    # It should have found direct.com and debunk.com
    assert len(output["supporting_evidence"]) == 1
    assert output["supporting_evidence"][0]["source"]["url"] == "http://direct.com"
    
    assert len(output["conflicting_evidence"]) == 1
    assert output["conflicting_evidence"][0]["source"]["url"] == "http://debunk.com"
    
    # It should have disputed verdict since there is both supporting and conflicting
    assert output["verdict"] == "disputed"

async def test_fact_check_agent_deduplication_bypass():
    agent = FactCheckAgent()
    claim = AtomicClaim(id="1", text="sky is blue", claim_type=ClaimType.FACT, confidence=0.5, support_status=EvidenceSupportStatus.UNSUPPORTED)
    
    input_data = {
        "claim": claim.model_dump(),
        "existing_source_urls": ["http://direct.com/"]  # Trailing slash
    }
    
    mock_tool_registry = AsyncMock()
    async def mock_call(tool_name, input_data, agent_id):
        if tool_name == "web_search":
            return MagicMock(success=True, data=[{"url": "http://direct.com", "title": "Direct"}]) # No trailing slash
        elif tool_name == "extract_content":
            return MagicMock(success=True, data=MagicMock(text="extracted"))
    
    mock_tool_registry.call.side_effect = mock_call
    agent.set_tool_registry(mock_tool_registry)
    
    mock_llm = AsyncMock()
    mock_plan = MagicMock()
    mock_plan.queries = ["test query"]
    mock_llm.generate_structured.return_value = mock_plan
    agent.set_llm_provider(mock_llm)
    
    # Run agent until completed
    await agent.step(input_data) # init
    await agent.step({}) # plan
    await agent.step({}) # search
    
    assert "http://direct.com" not in [s["url"] for s in agent.internal_state["search_results"]], "Deduplication failed due to trailing slash"

