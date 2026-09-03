"""Unit tests for FalsificationAgent (P5-16)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.falsification import FalsificationAgent
from app.agents.agent_contracts import FalsificationInput, FalsificationOutput, HypothesisItem
from app.agents.base import StepResult


@pytest.mark.asyncio
async def test_falsification_agent_inverse_queries():
    """Test generation of disconfirming / inverse search queries."""
    agent = FalsificationAgent()
    statement = "Quantum processors achieve 100x speedup for DB queries"
    queries = agent._generate_inverse_queries(statement)

    assert len(queries) == 4
    assert any("disproves" in q for q in queries)
    assert any("false" in q for q in queries)
    assert any("Counterarguments" in q for q in queries)


@pytest.mark.asyncio
async def test_falsification_agent_evidence_classification():
    """Test snippet classification into SUPPORTS, FALSIFIES, or NEUTRAL."""
    agent = FalsificationAgent()
    stmt = "AI models eliminate software bugs completely"

    # Falsifying snippet
    falsify_item = agent._classify_evidence(
        snippet_content="Studies show this claim is false and flawed, as AI models introduce subtle logic bugs.",
        source_url="https://refute.org",
        statement=stmt,
        query_used="Why is it false that AI eliminates bugs?"
    )
    assert falsify_item["relationship"] == "FALSIFIES"
    assert falsify_item["weight"] > 0.5

    # Supporting snippet
    support_item = agent._classify_evidence(
        snippet_content="Benchmarks confirm and prove that automated AI verification is true and accurate.",
        source_url="https://confirm.org",
        statement=stmt,
        query_used="Evidence supporting AI verification"
    )
    assert support_item["relationship"] == "SUPPORTS"
    assert support_item["weight"] > 0.5

    # Neutral snippet
    neutral_item = agent._classify_evidence(
        snippet_content="Software development involves code review and continuous deployment pipelines.",
        source_url="https://context.org",
        statement=stmt,
        query_used="General context"
    )
    assert neutral_item["relationship"] == "NEUTRAL"
    assert neutral_item["weight"] == 0.3


def test_calculate_confidence_math_and_edge_cases():
    """Test confidence calculation formula and zero-weight / boundary handling."""
    agent = FalsificationAgent()

    # 1. Empty evidence -> returns initial confidence
    assert agent.calculate_confidence(initial=0.7, evidence_items=[]) == 0.7

    # 2. Equal supporting and falsifying -> normalized to 0.5
    items_equal = [
        {"relationship": "SUPPORTS", "weight": 0.8},
        {"relationship": "FALSIFIES", "weight": 0.8}
    ]
    assert agent.calculate_confidence(initial=0.5, evidence_items=items_equal) == 0.5

    # 3. Only supporting evidence -> normalized to 1.0
    items_support = [
        {"relationship": "SUPPORTS", "weight": 1.0},
        {"relationship": "SUPPORTS", "weight": 0.5}
    ]
    assert agent.calculate_confidence(initial=0.5, evidence_items=items_support) == 1.0

    # 4. Only falsifying evidence -> normalized to 0.0
    items_falsify = [
        {"relationship": "FALSIFIES", "weight": 1.0}
    ]
    assert agent.calculate_confidence(initial=0.5, evidence_items=items_falsify) == 0.0

    # 5. Total weight == 0 -> returns initial confidence
    items_zero = [
        {"relationship": "NEUTRAL", "weight": 0.0}
    ]
    assert agent.calculate_confidence(initial=0.6, evidence_items=items_zero) == 0.6


@pytest.mark.asyncio
async def test_falsification_agent_max_attempts_enforcement():
    """Test that FalsificationAgent respects max_falsification_attempts limit."""
    agent = FalsificationAgent()
    input_data = {
        "hypothesis": {
            "hypothesis_id": "hyp-max-1",
            "statement": "Over-attempt test hypothesis",
            "initial_confidence": 0.5,
            "max_falsification_attempts": 2
        }
    }

    # Mock web search tool to prevent network calls
    agent.web_search_tool.search = AsyncMock(return_value=[])

    # Attempt 1
    res1 = await agent.step(input_data)
    assert res1.action == "falsify_search"

    # Attempt 2
    res2 = await agent.step(input_data)

    # Attempt 3 (exceeds max_falsification_attempts=2)
    res3 = await agent.step(input_data)
    assert res3.action == "stop"
    assert res3.should_continue is False
    assert "limit" in res3.message


@pytest.mark.asyncio
async def test_falsification_agent_compile_output():
    """Test compile_output produces valid FalsificationOutput schema dict."""
    agent = FalsificationAgent()
    agent._hypothesis_id = "hyp-99"
    agent._updated_confidence = 0.25
    agent._attempts_used = 2
    agent._evidence_items = [
        {"relationship": "FALSIFIES", "weight": 0.8}
    ]

    output = await agent.compile_output()
    assert output["hypothesis_id"] == "hyp-99"
    assert output["updated_confidence"] == 0.25
    assert output["attempts_used"] == 2
    assert len(output["evidence_items"]) == 1
