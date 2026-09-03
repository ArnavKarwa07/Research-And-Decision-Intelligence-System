"""Unit tests for CriticAgent (P5-16)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.critic import CriticAgent
from app.agents.agent_contracts import CriticInput, CriticOutput
from app.agents.base import StepResult


@pytest.mark.asyncio
async def test_critic_agent_initialization():
    """Test default agent configuration for CriticAgent."""
    agent = CriticAgent()
    assert agent.config.max_steps == 5
    assert agent.config.max_tokens == 15000
    assert agent.config.timeout_seconds == 45
    assert "llm_structured_generate" in agent.config.allowed_tools


@pytest.mark.asyncio
async def test_critic_agent_audits_weak_evidence():
    """Test CriticAgent flags single source and low confidence claims."""
    agent = CriticAgent()
    claims = [
        {
            "id": "c1",
            "confidence": 0.40,  # Low confidence (< 0.60)
            "support_status": "SUPPORTED",
            "sources": [{"url": "https://single-source.com"}]  # Single source
        },
        {
            "id": "c2",
            "confidence": 0.85,
            "support_status": "UNVERIFIED",  # Unverified
            "sources": []
        }
    ]

    input_data = {
        "synthesis": "Test synthesis summary focusing on software scaling.",
        "claims": claims,
        "evidence_chain": []
    }

    result: StepResult = await agent.step(input_data)

    assert result.action == "critique_pass"
    assert len(agent.weak_evidence) >= 2
    
    # Check single source reason
    reasons = [w["reason"] for w in agent.weak_evidence]
    assert "SINGLE_SOURCE" in reasons
    assert "LOW_CONFIDENCE" in reasons
    assert "UNVERIFIED" in reasons


@pytest.mark.asyncio
async def test_critic_agent_audits_omitted_variables():
    """Test CriticAgent detects missing key domain variables (e.g. cost, compliance)."""
    agent = CriticAgent()
    # Synthesis missing financial cost, compliance, risk
    input_data = {
        "synthesis": "The technical framework utilizes fast parallel execution algorithms.",
        "claims": [],
        "evidence_chain": []
    }

    await agent.step(input_data)

    missing_vars = [mv["variable"] for mv in agent.missing_variables]
    assert "financial_cost" in missing_vars
    assert "regulatory_compliance" in missing_vars
    assert "risk_mitigation" in missing_vars


@pytest.mark.asyncio
async def test_critic_agent_confirmation_bias_detection():
    """Test CriticAgent detects confirmation bias when 100% of claims are supported."""
    agent = CriticAgent()
    claims = [
        {"id": "c1", "confidence": 0.9, "support_status": "SUPPORTED", "sources": [{"url": "s1"}, {"url": "s2"}]},
        {"id": "c2", "confidence": 0.9, "support_status": "SUPPORTED", "sources": [{"url": "s1"}, {"url": "s2"}]},
        {"id": "c3", "confidence": 0.9, "support_status": "SUPPORTED", "sources": [{"url": "s1"}, {"url": "s2"}]}
    ]

    await agent.step({"synthesis": "All claims confirmed.", "claims": claims})

    assert any("Bias Alert" in f for f in agent.findings)


@pytest.mark.asyncio
async def test_critic_agent_severity_and_replan_recommendation():
    """Test severity level computation and replan recommendation logic."""
    agent = CriticAgent()
    # Plant a critical weak evidence item (confidence < 0.30)
    claims = [
        {"id": "c_crit", "confidence": 0.20, "support_status": "UNSUPPORTED", "sources": []}
    ]

    await agent.step({"synthesis": "Weak synthesis", "claims": claims})

    assert agent.overall_severity == "CRITICAL"
    assert agent.replan_recommended is True

    output = await agent.compile_output()
    assert output["overall_severity"] == "CRITICAL"
    assert output["replan_recommended"] is True
    assert len(output["recommendations"]) > 0
