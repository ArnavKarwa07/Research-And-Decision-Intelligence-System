"""Integration tests for Phase 5 LangGraph Pipeline.
Tests hypothesis, falsification, and critic nodes, full workflow execution,
and the should_replan conditional routing edge logic.
"""
import pytest
from langgraph.graph import END
from app.agents.graph import (
    create_langgraph_workflow,
    hypothesis_node,
    falsification_node,
    critic_node,
    should_replan,
    AgentState
)


@pytest.mark.asyncio
async def test_phase5_pipeline_full_execution():
    """Test full LangGraph workflow execution including Phase 5 nodes."""
    workflow = create_langgraph_workflow()

    initial_state: AgentState = {
        "query_id": "test-phase5-query",
        "text": "Analyze quantum computing cryptographic vulnerabilities",
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
        "search_queries": [],
        "summary": "",
        "confidence": 0.0,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 3,
        "audit_passed": False,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 0
    }

    merged_state = dict(initial_state)
    async for output in workflow.astream(initial_state, config={"recursion_limit": 50}):
        for node_name, state in output.items():
            merged_state.update(state)

    final_state = merged_state
    assert final_state is not None
    assert final_state.get("is_complete") is True
    assert "hypotheses" in final_state
    assert isinstance(final_state["hypotheses"], list)
    assert "falsification_results" in final_state
    assert isinstance(final_state["falsification_results"], list)
    assert "critique_report" in final_state
    assert final_state["critique_report"] is not None
    assert "overall_severity" in final_state
    assert final_state["current_step"] > 0


@pytest.mark.asyncio
async def test_hypothesis_falsification_critic_nodes():
    """Test individual Phase 5 nodes isolated execution."""
    base_state: AgentState = {
        "query_id": "test-node-query",
        "text": "AI alignment safety protocols",
        "mode": "deep",
        "plan": [],
        "steps": [],
        "snippets": [],
        "chunks": [],
        "claims": [
            {
                "id": "claim-1",
                "type": "FACT",
                "content": "AI alignment is critical.",
                "confidence": 0.9,
                "support_status": "SUPPORTED"
            }
        ],
        "scored_sources": [],
        "claim_source_links": [],
        "contradictions": [],
        "source_groups": [],
        "stale_source_ids": [],
        "fact_check_results": [],
        "verification_loop_count": 0,
        "decision_matrix": None,
        "search_queries": [],
        "summary": "Initial synthesis text.",
        "confidence": 0.85,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 3,
        "audit_passed": False,
        "audit_issues": [],
        "is_complete": False,
        "current_step": 1
    }

    # 1. Test Hypothesis Node
    hyp_output = await hypothesis_node(base_state)
    assert "hypotheses" in hyp_output
    assert len(hyp_output["hypotheses"]) > 0

    # Update state with hypotheses
    base_state["hypotheses"] = hyp_output["hypotheses"]
    base_state["steps"] = hyp_output["steps"]

    # 2. Test Falsification Node
    fals_output = await falsification_node(base_state)
    assert "falsification_results" in fals_output
    assert len(fals_output["falsification_results"]) == len(base_state["hypotheses"])

    # Update state with falsification results
    base_state["falsification_results"] = fals_output["falsification_results"]
    base_state["steps"] = fals_output["steps"]

    # 3. Test Critic Node
    crit_output = await critic_node(base_state)
    assert "critique_report" in crit_output
    assert "overall_severity" in crit_output
    assert "audit_passed" in crit_output
    assert crit_output["is_complete"] is True


def test_should_replan_conditional_edge():
    """Test the should_replan conditional routing edge and circuit breaker logic."""
    base_state: AgentState = {
        "query_id": "test-edge-query",
        "text": "Sample query",
        "mode": "fast",
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
        "search_queries": [],
        "summary": "",
        "confidence": 0.5,
        "hypotheses": [],
        "falsification_results": [],
        "critique_report": None,
        "overall_severity": "LOW",
        "replan_count": 0,
        "max_replan_iterations": 3,
        "audit_passed": True,
        "audit_issues": [],
        "is_complete": True,
        "current_step": 5
    }

    # Case 1: LOW severity -> should route to decision node
    base_state["overall_severity"] = "LOW"
    assert should_replan(base_state) in ["decision", END]

    # Case 2: MEDIUM severity -> should route to decision node
    base_state["overall_severity"] = "MEDIUM"
    assert should_replan(base_state) in ["decision", END]

    # Case 3: HIGH severity with remaining replan budget -> should route to research
    base_state["overall_severity"] = "HIGH"
    base_state["replan_count"] = 0
    base_state["max_replan_iterations"] = 3
    assert should_replan(base_state) == "research"

    # Case 4: CRITICAL severity with remaining replan budget -> should route to research
    base_state["overall_severity"] = "CRITICAL"
    base_state["replan_count"] = 2
    assert should_replan(base_state) == "research"

    # Case 5: Circuit Breaker - HIGH severity but budget exhausted -> should route to decision node
    base_state["overall_severity"] = "HIGH"
    base_state["replan_count"] = 3
    base_state["max_replan_iterations"] = 3
    assert should_replan(base_state) in ["decision", END]
