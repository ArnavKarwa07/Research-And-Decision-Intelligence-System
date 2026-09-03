"""Unit tests for HypothesisAgent (P5-16)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.hypothesis import HypothesisAgent
from app.agents.agent_contracts import HypothesisAgentInput, HypothesisAgentOutput, HypothesisItem
from app.agents.base import AgentConfig, StepResult


@pytest.mark.asyncio
async def test_hypothesis_agent_initialization():
    """Test default agent configuration."""
    agent = HypothesisAgent()
    assert agent.config.max_steps == 5
    assert agent.config.max_tokens == 15000
    assert agent.config.timeout_seconds == 45
    assert "llm_generate" in agent.config.allowed_tools


@pytest.mark.asyncio
async def test_hypothesis_agent_fallback_generation():
    """Test hypothesis agent step produces 3-7 hypotheses via fallback when LLM is unavailable."""
    agent = HypothesisAgent()
    input_data = {
        "query_text": "Does quantum computing threaten current RSA encryption?",
        "existing_claims": [],
        "existing_sources": []
    }

    result: StepResult = await agent.step(input_data)

    assert result.action == "generate_hypotheses"
    assert result.should_continue is False
    assert "hypotheses" in result.result
    
    hypotheses = result.result["hypotheses"]
    assert 3 <= len(hypotheses) <= 7

    output = await agent.compile_output()
    assert "hypotheses" in output
    assert len(output["hypotheses"]) == len(hypotheses)
    assert len(output["investigation_priorities"]) > 0


@pytest.mark.asyncio
async def test_hypothesis_agent_enforces_3_to_7_items_boundary():
    """Test hypothesis agent caps generated hypotheses to at most 7 items."""
    agent = HypothesisAgent()
    
    # Mock LLM provider returning 10 hypotheses
    mock_llm = MagicMock()
    items = [
        HypothesisItem(
            hypothesis_id=f"h-{i}",
            statement=f"Hypothesis {i}",
            initial_confidence=0.5,
            discriminating_evidence_needed=[f"Evidence {i}"]
        )
        for i in range(10)
    ]
    mock_llm.generate_structured = AsyncMock(return_value=HypothesisAgentOutput(
        hypotheses=items,
        investigation_priorities=["Priority 1"]
    ))
    agent.set_llm_provider(mock_llm)

    await agent.step({"query_text": "Sample Query"})
    output = await agent.compile_output()

    # Must be capped to at most 7
    assert len(output["hypotheses"]) == 7


@pytest.mark.asyncio
async def test_hypothesis_agent_contract_typing():
    """Test HypothesisAgentInput and Output typing contract."""
    inp = HypothesisAgentInput(
        query_text="What is the impact of remote work on productivity?",
        existing_claims=[{"id": "c1", "text": "Productivity increased"}],
        existing_sources=[{"url": "https://example.com"}]
    )
    assert inp.query_text == "What is the impact of remote work on productivity?"
    assert len(inp.existing_claims) == 1

    item = HypothesisItem(
        hypothesis_id="hyp-1",
        statement="Remote work increases worker satisfaction.",
        initial_confidence=0.7,
        discriminating_evidence_needed=["Survey data"]
    )
    out = HypothesisAgentOutput(hypotheses=[item], investigation_priorities=["Survey analysis"])
    assert len(out.hypotheses) == 1
    assert out.hypotheses[0].initial_confidence == 0.7
