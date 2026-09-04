"""Integration tests for SupervisorAgent budget gates and dynamic budgeting synthesis."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.supervisor import (
    SupervisorAgent,
    SupervisorInput,
    ResearchPlan,
    ResearchObjective,
)
from app.agents.base import AgentConfig, StepResult
from app.services.budget_service import budget_service, BudgetExceededError


@pytest.fixture(autouse=True)
def cleanup_budget_service():
    """Ensure clean budget service state before and after each test."""
    yield
    # Cleanup any registered test run budgets
    for rid in ["run-sup-1", "run-sup-budget-cap", "run-sup-tool-error"]:
        budget_service.cleanup(rid)


@pytest.mark.asyncio
async def test_supervisor_normal_flow_with_mock_llm():
    """Test standard supervisor flow when budget is sufficient."""
    agent = SupervisorAgent()

    mock_llm = MagicMock()
    plan = ResearchPlan(
        objectives=[
            ResearchObjective(query="test query 1", objective="Objective 1", depth="shallow"),
        ],
        reasoning="Test plan reasoning"
    )
    mock_llm.generate_structured = AsyncMock(return_value=plan)
    mock_llm.generate = AsyncMock(return_value=MagicMock(content="Final summary statement.", tokens_used=100))
    agent.set_llm_provider(mock_llm)

    mock_registry = MagicMock()
    mock_registry.call = AsyncMock(return_value=MagicMock(
        success=True,
        data={"evidence": [{"source": "web", "content": "Evidence item 1"}]}
    ))
    agent.set_tool_registry(mock_registry)

    input_data = {
        "query_text": "What is RADIS architecture?",
        "session_id": "session-123",
        "run_id": "run-sup-1"
    }

    # Step 1: Planning
    res1 = await agent.step(input_data)
    assert res1.action == "plan_research"
    assert agent.internal_state["phase"] == "researching"

    # Step 2: Execute Research
    res2 = await agent.step({})
    assert res2.action == "spawn_agent"
    assert len(agent.internal_state["evidence"]) == 1

    # Step 3: Execute Research (no more unprocessed objectives) -> Evaluating
    res3 = await agent.step({})
    assert res3.action == "spawn_agents"
    assert agent.internal_state["phase"] == "evaluating"

    # Step 4: Evaluating -> Synthesizing
    res4 = await agent.step({})
    assert res4.action == "evaluate"
    assert agent.internal_state["phase"] == "synthesizing"

    # Step 5: Synthesizing -> Done
    res5 = await agent.step({})
    assert res5.action == "synthesize"
    assert agent.internal_state["phase"] == "done"
    assert res5.should_continue is False

    output = await agent.compile_output()
    assert output["summary"] == "Final summary statement."
    assert len(output["evidence_list"]) == 1


@pytest.mark.asyncio
async def test_supervisor_budget_exhaustion_gate_trigger():
    """Test that supervisor budget check gate caps research and triggers immediate synthesis on budget exhaustion."""
    run_id = "run-sup-budget-cap"
    # Create run budget with strict limit of 100 tokens
    budget_service.create_run_budget(run_id=run_id, max_tokens=100)

    agent = SupervisorAgent()

    mock_llm = MagicMock()
    plan = ResearchPlan(
        objectives=[
            ResearchObjective(query="q1", objective="Obj 1", depth="shallow"),
            ResearchObjective(query="q2", objective="Obj 2", depth="shallow"),
        ],
        reasoning="Multi-objective plan"
    )
    mock_llm.generate_structured = AsyncMock(return_value=plan)
    mock_llm.generate = AsyncMock(return_value=MagicMock(content="Capped summary", tokens_used=50))
    agent.set_llm_provider(mock_llm)

    mock_registry = MagicMock()
    mock_registry.call = AsyncMock(return_value=MagicMock(
        success=True,
        data={"evidence": [{"id": "ev-1", "text": "First evidence piece"}]}
    ))
    agent.set_tool_registry(mock_registry)

    input_data = {
        "query_text": "Exhaustion test query",
        "session_id": "session-cap",
        "run_id": run_id
    }

    # Step 1: Planning
    await agent.step(input_data)
    assert agent.internal_state["phase"] == "researching"

    # Step 2: Dispatch obj 1 -> succeeds
    res_obj1 = await agent.step({})
    assert res_obj1.action == "spawn_agent"
    assert len(agent.internal_state["evidence"]) == 1

    # Record usage in budget service to exceed the hard token limit
    rb = budget_service.get_run_budget(run_id)
    if rb:
        rb.token_budget.prompt_tokens = 80
        rb.token_budget.completion_tokens = 50

    # Step 3: Dispatch obj 2 -> Budget Check Gate triggers!
    res_gate = await agent.step({})
    assert res_gate.action == "cap_research"
    assert "Budget exhausted" in res_gate.message
    assert agent.internal_state["phase"] == "synthesizing"
    assert agent.internal_state["budget_capped"] is True

    # Step 4: Immediate synthesis with accumulated evidence
    res_synth = await agent.step({})
    assert res_synth.action == "synthesize"
    assert agent.internal_state["phase"] == "done"
    assert res_synth.should_continue is False

    output = await agent.compile_output()
    assert "[BUDGET CAPPED]" in output["summary"]
    assert len(output["evidence_list"]) == 1
    assert output["evidence_list"][0]["id"] == "ev-1"


@pytest.mark.asyncio
async def test_supervisor_handles_budget_exceeded_error_exception():
    """Test that supervisor catches BudgetExceededError during tool execution and triggers synthesis gracefully."""
    run_id = "run-sup-tool-error"
    agent = SupervisorAgent()

    mock_llm = MagicMock()
    plan = ResearchPlan(
        objectives=[ResearchObjective(query="q1", objective="Obj 1", depth="shallow")],
        reasoning="Test plan"
    )
    mock_llm.generate_structured = AsyncMock(return_value=plan)
    mock_llm.generate = AsyncMock(return_value=MagicMock(content="Capped summary", tokens_used=20))
    agent.set_llm_provider(mock_llm)

    # Mock tool registry to raise BudgetExceededError when spawning agent
    mock_registry = MagicMock()
    mock_registry.call = AsyncMock(side_effect=BudgetExceededError("tokens", 500, 400, run_id=run_id))
    agent.set_tool_registry(mock_registry)

    input_data = {
        "query_text": "Error test query",
        "session_id": "session-err",
        "run_id": run_id
    }

    # Step 1: Planning
    await agent.step(input_data)

    # Step 2: Tool execution raises BudgetExceededError -> caught, research capped
    res_err = await agent.step({})
    assert res_err.action == "cap_research"
    assert agent.internal_state["phase"] == "synthesizing"
    assert agent.internal_state["budget_capped"] is True

    # Step 3: Synthesis completes
    res_synth = await agent.step({})
    assert res_synth.action == "synthesize"
    assert agent.internal_state["phase"] == "done"
