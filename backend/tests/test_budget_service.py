"""Unit tests for BudgetService and multi-dimension budget enforcement."""

import time
import pytest
from unittest.mock import MagicMock

from app.services.budget_service import (
    BudgetExceededError,
    BudgetService,
    CompositeBudget,
    SearchBudget,
    TokenBudget,
    ToolBudget,
    WallClockBudget,
)


def test_token_budget_usage_and_limits():
    tb = TokenBudget(max_tokens=1000, soft_limit_tokens=800)
    assert tb.total_tokens == 0
    assert tb.remaining() == 1000
    assert tb.utilization() == 0.0
    assert not tb.is_soft_limit_exceeded()
    assert not tb.is_hard_limit_exceeded()

    tb.record_usage(prompt_tokens=500, completion_tokens=300)
    assert tb.total_tokens == 800
    assert tb.remaining() == 200
    assert tb.utilization() == 0.8
    assert tb.is_soft_limit_exceeded()
    assert not tb.is_hard_limit_exceeded()

    tb.record_usage(prompt_tokens=100, completion_tokens=100)
    assert tb.total_tokens == 1000
    assert tb.remaining() == 0
    assert tb.utilization() == 1.0
    assert tb.is_hard_limit_exceeded()


def test_search_budget_usage_and_limits():
    sb = SearchBudget(max_searches=10, soft_limit_searches=8)
    assert sb.remaining() == 10
    sb.record_usage(7)
    assert not sb.is_soft_limit_exceeded()

    sb.record_usage(1)
    assert sb.is_soft_limit_exceeded()
    assert not sb.is_hard_limit_exceeded()

    sb.record_usage(2)
    assert sb.is_hard_limit_exceeded()


def test_tool_budget_usage_and_limits():
    tb = ToolBudget(max_tool_calls=5, soft_limit_tool_calls=4)
    tb.record_usage(4)
    assert tb.is_soft_limit_exceeded()
    assert not tb.is_hard_limit_exceeded()

    tb.record_usage(1)
    assert tb.is_hard_limit_exceeded()


def test_wall_clock_budget():
    wcb = WallClockBudget(max_seconds=10.0, soft_limit_seconds=8.0)
    assert wcb.elapsed_seconds >= 0.0
    assert not wcb.is_hard_limit_exceeded()

    # Freeze elapsed time for precise assertion
    wcb._frozen_elapsed = 8.5
    assert wcb.is_soft_limit_exceeded()
    assert not wcb.is_hard_limit_exceeded()

    wcb._frozen_elapsed = 11.0
    assert wcb.is_hard_limit_exceeded()
    assert wcb.remaining() == 0.0


def test_composite_budget_enforcement():
    cb = CompositeBudget(
        token_budget=TokenBudget(max_tokens=100, soft_limit_tokens=80),
        search_budget=SearchBudget(max_searches=5, soft_limit_searches=4),
        tool_budget=ToolBudget(max_tool_calls=10, soft_limit_tool_calls=8),
        wall_clock_budget=WallClockBudget(max_seconds=60.0),
    )

    cb.token_budget.record_usage(prompt_tokens=50, completion_tokens=35)
    warnings = cb.enforce()
    assert len(warnings) == 1
    assert "Token budget soft limit reached" in warnings[0]

    cb.search_budget.record_usage(5)
    with pytest.raises(BudgetExceededError) as exc_info:
        cb.enforce()
    assert exc_info.value.dimension == "searches"
    assert exc_info.value.current == 5.0
    assert exc_info.value.limit == 5.0


def test_budget_service_sub_task_allocation_and_record():
    service = BudgetService()
    run_id = "run-test-123"

    parent_budget = service.create_run_budget(
        run_id=run_id,
        max_tokens=1000,
        max_searches=10,
        max_tool_calls=20,
        max_seconds=100.0,
    )

    sub_budget = service.create_sub_task_budget(
        run_id=run_id,
        sub_task_id="sub-task-1",
        max_tokens=500,
        max_searches=3,
    )

    assert sub_budget.token_budget.max_tokens == 500
    assert sub_budget.search_budget.max_searches == 3

    # Record usage for sub-task
    warnings = service.record_usage(
        run_id=run_id,
        sub_task_id="sub-task-1",
        prompt_tokens=200,
        completion_tokens=250,  # total 450 (soft limit for 500 is 400)
        searches=1,
        tool_calls=2,
    )

    # Parent budget should also update
    assert parent_budget.token_budget.total_tokens == 450
    assert parent_budget.search_budget.searches_conducted == 1
    assert parent_budget.tool_budget.tool_calls == 2

    # Sub-task soft limit warning
    assert any("Token budget soft limit reached" in w for w in warnings)

    # Sub-task hard limit violation
    with pytest.raises(BudgetExceededError) as exc_info:
        service.record_usage(
            run_id=run_id,
            sub_task_id="sub-task-1",
            searches=3,  # Total searches = 4 > sub-task limit of 3
        )
    assert exc_info.value.dimension == "searches"


def test_budget_service_update_agent_run_model():
    service = BudgetService()
    run_id = "550e8400-e29b-41d4-a716-446655440000"

    service.create_run_budget(run_id=run_id, max_tokens=2000)
    service.record_usage(run_id=run_id, prompt_tokens=300, completion_tokens=200)

    # Mock AgentRun object
    mock_agent_run = MagicMock()
    mock_agent_run.id = run_id
    mock_agent_run.execution_log = {}

    mock_db = MagicMock()

    service.update_agent_run_model(mock_db, mock_agent_run)

    assert mock_agent_run.tokens_used == 500
    assert "budget_stats" in mock_agent_run.execution_log
    assert mock_agent_run.execution_log["budget_stats"]["tokens"]["total"] == 500
    mock_db.add.assert_called_once_with(mock_agent_run)
