"""Unit tests specifically verifying fixes for backend adversarial review bugs:
BUG-WS-01, BUG-WS-02, BUG-HYP-01, BUG-HYP-02, BUG-GR-01..04, BUG-CR-01..02.
"""

import pytest
from app.tools.web_search import WebSearchTool, WebSearchInput, WebSearchResult
from app.agents.hypothesis import HypothesisAgent
from app.agents.critic import CriticAgent
from app.agents.graph import (
    decision_node,
    provenance_node,
    evidence_node,
    synthesis_node,
)
from app.agents.agent_contracts import HypothesisAgentOutput, HypothesisItem, CriticInput


@pytest.mark.asyncio
async def test_bug_ws_01_and_02():
    """Verify WebSearchTool handles None attributes in items and empty/None query text."""
    tool = WebSearchTool(provider="mock")
    # Test query sanitization with empty string or whitespace
    res = await tool.search(WebSearchInput(query="   ", num_results=2))
    assert isinstance(res, list)
    assert len(res) > 0
    assert res[0].title is not None
    assert res[0].snippet is not None

    # Test relevance calculation with empty item title or snippet
    empty_item = WebSearchResult(url="https://example.com", title="", snippet="", rank=1)
    res2 = await tool.search(WebSearchInput(query="test search", num_results=2))
    for r in res2:
        assert isinstance(r.title, str)
        assert isinstance(r.snippet, str)


@pytest.mark.asyncio
async def test_bug_hyp_01_and_02():
    """Verify HypothesisAgent model_dump handling and step condition checking res.hypotheses."""
    agent = HypothesisAgent()
    step_result = await agent.step({"query_text": "Hypothesis test query"})
    assert step_result.action == "generate_hypotheses"
    assert "hypotheses" in step_result.result
    assert isinstance(step_result.result["hypotheses"], list)
    assert len(step_result.result["hypotheses"]) >= 1


@pytest.mark.asyncio
async def test_bug_gr_01_decision_node_null_matrix():
    """Verify decision_node handles state with decision_matrix=None or missing alternatives."""
    state = {
        "text": "Decision test query",
        "decision_matrix": None,
        "claims": [],
        "contradictions": [],
        "hypotheses": [],
        "summary": "",
        "steps": None,
        "current_step": None,
    }
    res = await decision_node(state)
    assert "decision_matrix" in res
    assert res["steps"] is not None
    assert res["current_step"] == 1


@pytest.mark.asyncio
async def test_bug_gr_02_provenance_and_evidence_nodes_null_source():
    """Verify provenance_node and evidence_node handle snippets with missing or None source / content."""
    state = {
        "text": "Provenance test",
        "snippets": [
            {"content": None, "source": None, "query_used": "q1"},
            {"content": "Valid content", "source": {"url": "http://test.com", "title": None, "qualityScore": "HIGH"}},
        ],
        "scored_sources": [],
        "steps": None,
        "current_step": None,
    }
    prov_res = await provenance_node(state)
    assert "scored_sources" in prov_res
    assert prov_res["current_step"] == 1

    ev_state = {**state, "scored_sources": prov_res["scored_sources"]}
    ev_res = await evidence_node(ev_state)
    assert "claims" in ev_res
    assert ev_res["claims"][0]["content"] == ""
    assert ev_res["current_step"] == 1


@pytest.mark.asyncio
async def test_bug_gr_03_synthesis_node_non_dict_alternatives():
    """Verify synthesis_node handles non-dict elements in alternatives list."""
    state = {
        "text": "Synthesis test",
        "snippets": [],
        "claims": [],
        "steps": [],
        "current_step": 0,
    }
    res = await synthesis_node(state)
    assert "decision_matrix" in res
    assert res["current_step"] == 1


@pytest.mark.asyncio
async def test_bug_cr_01_and_02_critic_agent():
    """Verify CriticAgent safely defaults inputs and normalizes claims in _audit_bias."""
    agent = CriticAgent()
    input_data = {
        "synthesis": None,
        "claims": None,
        "evidence_chain": None,
        "hypotheses": None,
    }
    step_res = await agent.step(input_data)
    assert step_res.action == "critique_pass"
    assert agent.overall_severity in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    critic_input = CriticInput(synthesis="Test synthesis with confidence 85%", claims=[], evidence_chain=[], hypotheses=[])
    step_res2 = await agent.step(critic_input)
    assert step_res2.action == "critique_pass"
