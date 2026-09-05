import pytest
import asyncio
from app.agents.synthesis import SynthesisAgent
from app.agents.base import AgentConfig
from app.agents.graph import synthesis_node, route_after_decision, route_after_synthesis, AgentState

@pytest.mark.asyncio
async def test_synthesis_agent_react_topic_no_jargon():
    config = AgentConfig(max_steps=5, max_tokens=10000, timeout_seconds=60, allowed_tools=[])
    agent = SynthesisAgent(config)
    input_data = {
        "objective": "which is better for me as a fresher react js vs fullstack",
        "claims": [{"content": "React is widely used for frontend web dev", "type": "FACT", "confidence": 0.9}],
        "sources": []
    }
    res = await agent.step(input_data)
    matrix = res.result
    
    assert "Monolithic Execution" not in str(matrix)
    assert "Multi-Agent Parallel Runtime" not in str(matrix)
    
    alternatives = matrix.get("alternatives", [])
    assert len(alternatives) >= 2
    assert any("react" in str(alt).lower() for alt in alternatives)


@pytest.mark.asyncio
async def test_synthesis_node_no_corporate_jargon():
    state: AgentState = {
        "query_id": "test-q1",
        "text": "which is better for me as a fresher react js",
        "mode": "deep",
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
        "confidence": 0.0,
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
        "run_id": None,
        "is_paused": False,
        "is_cancelled": False,
        "pause_requested": False,
        "cancel_requested": False,
        "active_checkpoint_id": None,
        "project_id": None,
        "session_id": None,
        "domain": None,
        "memory_context": None,
        "harvested_memory_items": None,
        "monitoring_job_id": None,
        "monitoring_output": None
    }

    res_state = await synthesis_node(state)
    matrix = res_state.get("decision_matrix", {})
    report = matrix.get("research_report", "")

    # Ensure no generic supply chain / lithography / regional buffer jargon is present
    assert "Regional Buffer Architecture" not in report
    assert "lithography" not in report.lower()
    assert "fabrication lead times" not in report.lower()

    # Ensure alternatives are relevant to the query topic
    alts = matrix.get("alternatives", [])
    assert len(alts) >= 2
    assert any("fresher" in alt["name"].lower() or "react" in str(alt).lower() or "strategy" in alt["name"].lower() for alt in alts)


def test_dynamic_graph_routing():
    state_simple: AgentState = {
        "text": "which is better for me as a fresher react js",
        "mode": "quick",
        "project_id": None,
        "session_id": None,
        "monitoring_job_id": None
    } # type: ignore

    # Quick mode routes directly from synthesis to decision and skips deep hypothesis pass
    assert route_after_synthesis(state_simple) == "decision"
    # Simple query without SQL/data keywords routes to memory node
    assert route_after_decision(state_simple) == "memory"

    state_data: AgentState = {
        "text": "show me sales metrics database table",
        "mode": "quick",
        "project_id": None,
        "session_id": None,
        "monitoring_job_id": None
    } # type: ignore

    # Query with database/metrics keywords routes to data node
    assert route_after_decision(state_data) == "data"
