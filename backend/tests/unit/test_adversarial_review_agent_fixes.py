"""Unit tests for adversarial code review fixes across graph.py, synthesis.py, and decision.py."""

import pytest
from app.agents.graph import (
    AgentState,
    route_after_decision,
    route_after_visualization,
    route_after_memory,
    research_node,
    synthesis_node,
    data_node,
    visualization_node,
)
from app.agents.synthesis import SynthesisAgent
from app.agents.decision import DecisionAgent
from app.agents.base import AgentConfig
from app.agents.agent_contracts import AlternativeOption


@pytest.mark.asyncio
async def test_route_after_decision_skips_data_on_non_quantitative():
    state: AgentState = {
        "query_id": "q-1",
        "text": "Analyze European data privacy regulations and compliance frameworks",
        "mode": "comprehensive",
        "plan": [],
        "steps": [],
        "snippets": [],
        "chunks": [],
        "claims": [],
        "scored_sources": [],
        "claim_source_links": [],
        "contradictions": [],
        "source_groups": [],
        "stale_source_ids": [],
        "fact_check_results": [],
        "verification_loop_count": 0,
        "decision_matrix": None,
        "data_analysis_results": None,
        "visualization_spec": None,
        "search_queries": [],
        "summary": "",
        "confidence": 0.9,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 3,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0,
        "run_id": "r-1",
        "is_paused": None,
        "is_cancelled": None,
        "pause_requested": None,
        "cancel_requested": None,
        "active_checkpoint_id": None,
        "project_id": "p-123",
        "session_id": None,
        "domain": None,
        "memory_context": None,
        "harvested_memory_items": None,
        "monitoring_job_id": "mon-123",
    }

    # Should route to memory because it's non-quantitative (despite having the word 'data')
    next_node = route_after_decision(state)
    assert next_node == "memory"

    # From memory, it should route to monitoring because monitoring_job_id is set
    assert route_after_memory(state) == "monitoring"


@pytest.mark.asyncio
async def test_route_after_decision_triggers_data_on_quantitative():
    state: AgentState = {
        "text": "Plot sales metrics by region in SQL database",
        "project_id": "p-123",
        "monitoring_job_id": "mon-123",
    }
    assert route_after_decision(state) == "data"
    assert route_after_visualization(state) == "memory"


@pytest.mark.asyncio
async def test_research_node_handles_missing_search_queries():
    state: AgentState = {
        "query_id": "q-2",
        "text": "Fallback Research Query",
        "mode": "quick",
        "steps": [],
        "current_step": 0,
    }
    res = await research_node(state)
    assert len(res["snippets"]) > 0
    assert res["current_step"] == 1


@pytest.mark.asyncio
async def test_synthesis_node_handles_none_confidence_and_claims():
    state: AgentState = {
        "query_id": "q-3",
        "text": "Test Null Handling Query",
        "claims": [{"content": "Claim 1", "confidence": None}, {"content": "Claim 2"}],
        "steps": [],
        "current_step": 0,
    }
    res = await synthesis_node(state)
    assert res["confidence"] == 0.92
    assert "decision_matrix" in res


@pytest.mark.asyncio
async def test_synthesis_agent_handles_nested_sources():
    config = AgentConfig(max_steps=5, max_tokens=1000, timeout_seconds=60, allowed_tools=[])
    agent = SynthesisAgent(config=config)
    input_data = {
        "objective": "Test Nested Sources",
        "claims": [
            {
                "content": "Claim with nested source",
                "source": {
                    "url": "https://example.com/report",
                    "title": "Example Report",
                    "qualityScore": "HIGH",
                },
            }
        ],
    }
    step_res = await agent.step(input_data)
    assert len(agent.sources_used) == 1
    assert agent.sources_used[0].url == "https://example.com/report"


@pytest.mark.asyncio
async def test_decision_agent_handles_pydantic_alternatives_and_null_topic():
    agent = DecisionAgent()
    alt_1 = AlternativeOption(name="Alt 1", pros=["Pro 1"], cons=["Con 1"], score=0.9)
    alt_2 = AlternativeOption(name="Alt 2", pros=["Pro 2"], cons=["Con 2"], score=0.7)

    input_data = {
        "alternatives": [alt_1, alt_2],
        "criteria": [{"id": "c1", "name": "Cost", "weight": 0.5}, {"id": "c2", "name": "Quality", "weight": 0.5}],
        "query_text": None,
    }

    res_step1 = await agent.step(input_data)
    assert res_step1.action == "compare_options"

    agent.state.steps_taken = 3
    res_step4 = await agent.step(input_data)
    assert res_step4.action == "finalize_decision"
