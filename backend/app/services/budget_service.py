"""Budget Service for Multi-Dimension Agent Budget Enforcement.

Enforces multi-dimension budgets (TokenBudget, SearchBudget, ToolBudget, WallClockBudget)
with hard and soft limits per run and sub-workstream / sub-task.
"""
from dataclasses import dataclass, field
import time
from typing import Any, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


class BudgetExceededError(Exception):
    """Exception raised when a hard budget limit is exceeded."""

    def __init__(self, dimension: str, current: float, limit: float, run_id: str | None = None, sub_task_id: str | None = None):
        self.dimension = dimension
        self.current = current
        self.limit = limit
        self.run_id = run_id
        self.sub_task_id = sub_task_id
        task_str = f" in sub-task {sub_task_id}" if sub_task_id else ""
        run_str = f" for run {run_id}" if run_id else ""
        super().__init__(f"Hard budget limit exceeded for '{dimension}'{run_str}{task_str}: {current} > {limit}")


@dataclass
class TokenBudget:
    """Token budget tracking prompt and completion tokens."""
    max_tokens: int = 100_000
    soft_limit_tokens: Optional[int] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0

    def __post_init__(self):
        if self.soft_limit_tokens is None:
            self.soft_limit_tokens = int(self.max_tokens * 0.8)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def record_usage(self, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens

    def is_soft_limit_exceeded(self) -> bool:
        if self.soft_limit_tokens is None:
            return False
        return self.total_tokens >= self.soft_limit_tokens

    def is_hard_limit_exceeded(self) -> bool:
        return self.total_tokens >= self.max_tokens

    def remaining(self) -> int:
        return max(0, self.max_tokens - self.total_tokens)

    def utilization(self) -> float:
        if self.max_tokens == 0:
            return 1.0
        return min(1.0, self.total_tokens / self.max_tokens)


@dataclass
class SearchBudget:
    """Search budget tracking web and database search calls."""
    max_searches: int = 20
    soft_limit_searches: Optional[int] = None
    searches_conducted: int = 0

    def __post_init__(self):
        if self.soft_limit_searches is None:
            self.soft_limit_searches = int(self.max_searches * 0.8)

    def record_usage(self, count: int = 1) -> None:
        self.searches_conducted += count

    def is_soft_limit_exceeded(self) -> bool:
        if self.soft_limit_searches is None:
            return False
        return self.searches_conducted >= self.soft_limit_searches

    def is_hard_limit_exceeded(self) -> bool:
        return self.searches_conducted >= self.max_searches

    def remaining(self) -> int:
        return max(0, self.max_searches - self.searches_conducted)

    def utilization(self) -> float:
        if self.max_searches == 0:
            return 1.0
        return min(1.0, self.searches_conducted / self.max_searches)


@dataclass
class ToolBudget:
    """Tool budget tracking aggregate tool calls."""
    max_tool_calls: int = 50
    soft_limit_tool_calls: Optional[int] = None
    tool_calls: int = 0

    def __post_init__(self):
        if self.soft_limit_tool_calls is None:
            self.soft_limit_tool_calls = int(self.max_tool_calls * 0.8)

    def record_usage(self, count: int = 1) -> None:
        self.tool_calls += count

    def is_soft_limit_exceeded(self) -> bool:
        if self.soft_limit_tool_calls is None:
            return False
        return self.tool_calls >= self.soft_limit_tool_calls

    def is_hard_limit_exceeded(self) -> bool:
        return self.tool_calls >= self.max_tool_calls

    def remaining(self) -> int:
        return max(0, self.max_tool_calls - self.tool_calls)

    def utilization(self) -> float:
        if self.max_tool_calls == 0:
            return 1.0
        return min(1.0, self.tool_calls / self.max_tool_calls)


@dataclass
class WallClockBudget:
    """Wall-clock time budget tracking execution duration."""
    max_seconds: float = 300.0
    soft_limit_seconds: Optional[float] = None
    start_time: float = field(default_factory=time.time)
    _frozen_elapsed: Optional[float] = None

    def __post_init__(self):
        if self.soft_limit_seconds is None:
            self.soft_limit_seconds = self.max_seconds * 0.8

    @property
    def elapsed_seconds(self) -> float:
        if self._frozen_elapsed is not None:
            return self._frozen_elapsed
        return max(0.0, time.time() - self.start_time)

    def freeze(self) -> None:
        """Freeze elapsed time for testing or completion."""
        self._frozen_elapsed = self.elapsed_seconds

    def is_soft_limit_exceeded(self) -> bool:
        if self.soft_limit_seconds is None:
            return False
        return self.elapsed_seconds >= self.soft_limit_seconds

    def is_hard_limit_exceeded(self) -> bool:
        return self.elapsed_seconds >= self.max_seconds

    def remaining(self) -> float:
        return max(0.0, self.max_seconds - self.elapsed_seconds)

    def utilization(self) -> float:
        if self.max_seconds == 0:
            return 1.0
        return min(1.0, self.elapsed_seconds / self.max_seconds)


class CompositeBudget:
    """Composite multi-dimension budget combining Token, Search, Tool, and WallClock budgets."""

    def __init__(
        self,
        token_budget: Optional[TokenBudget] = None,
        search_budget: Optional[SearchBudget] = None,
        tool_budget: Optional[ToolBudget] = None,
        wall_clock_budget: Optional[WallClockBudget] = None,
        run_id: str | None = None,
        sub_task_id: str | None = None,
    ):
        self.token_budget = token_budget or TokenBudget()
        self.search_budget = search_budget or SearchBudget()
        self.tool_budget = tool_budget or ToolBudget()
        self.wall_clock_budget = wall_clock_budget or WallClockBudget()
        self.run_id = run_id
        self.sub_task_id = sub_task_id

    def check_limits(self) -> tuple[bool, Optional[str], list[str]]:
        """
        Check all budget dimensions.
        Returns: (hard_exceeded: bool, hard_reason: str|None, soft_warnings: list[str])
        """
        soft_warnings = []
        hard_exceeded = False
        hard_reason = None

        if self.token_budget.is_hard_limit_exceeded():
            hard_exceeded = True
            hard_reason = f"Token budget hard limit exceeded ({self.token_budget.total_tokens}/{self.token_budget.max_tokens})"
        elif self.token_budget.is_soft_limit_exceeded():
            soft_warnings.append(f"Token budget soft limit reached ({self.token_budget.total_tokens}/{self.token_budget.soft_limit_tokens})")

        if self.search_budget.is_hard_limit_exceeded():
            hard_exceeded = True
            hard_reason = hard_reason or f"Search budget hard limit exceeded ({self.search_budget.searches_conducted}/{self.search_budget.max_searches})"
        elif self.search_budget.is_soft_limit_exceeded():
            soft_warnings.append(f"Search budget soft limit reached ({self.search_budget.searches_conducted}/{self.search_budget.soft_limit_searches})")

        if self.tool_budget.is_hard_limit_exceeded():
            hard_exceeded = True
            hard_reason = hard_reason or f"Tool budget hard limit exceeded ({self.tool_budget.tool_calls}/{self.tool_budget.max_tool_calls})"
        elif self.tool_budget.is_soft_limit_exceeded():
            soft_warnings.append(f"Tool budget soft limit reached ({self.tool_budget.tool_calls}/{self.tool_budget.soft_limit_tool_calls})")

        if self.wall_clock_budget.is_hard_limit_exceeded():
            hard_exceeded = True
            hard_reason = hard_reason or f"Wall clock budget hard limit exceeded ({self.wall_clock_budget.elapsed_seconds:.1f}s/{self.wall_clock_budget.max_seconds:.1f}s)"
        elif self.wall_clock_budget.is_soft_limit_exceeded():
            soft_warnings.append(f"Wall clock budget soft limit reached ({self.wall_clock_budget.elapsed_seconds:.1f}s/{self.wall_clock_budget.soft_limit_seconds:.1f}s)")

        return hard_exceeded, hard_reason, soft_warnings

    def enforce(self) -> list[str]:
        """
        Check limits and raise BudgetExceededError if any hard limit is exceeded.
        Returns soft warning messages if any soft limit is exceeded.
        """
        hard_exceeded, hard_reason, soft_warnings = self.check_limits()
        if hard_exceeded:
            dimension = "unknown"
            current = 0.0
            limit = 0.0
            if self.token_budget.is_hard_limit_exceeded():
                dimension = "tokens"
                current = float(self.token_budget.total_tokens)
                limit = float(self.token_budget.max_tokens)
            elif self.search_budget.is_hard_limit_exceeded():
                dimension = "searches"
                current = float(self.search_budget.searches_conducted)
                limit = float(self.search_budget.max_searches)
            elif self.tool_budget.is_hard_limit_exceeded():
                dimension = "tools"
                current = float(self.tool_budget.tool_calls)
                limit = float(self.tool_budget.max_tool_calls)
            elif self.wall_clock_budget.is_hard_limit_exceeded():
                dimension = "wall_clock_seconds"
                current = self.wall_clock_budget.elapsed_seconds
                limit = self.wall_clock_budget.max_seconds

            raise BudgetExceededError(dimension, current, limit, run_id=self.run_id, sub_task_id=self.sub_task_id)

        return soft_warnings

    def get_summary(self) -> dict[str, Any]:
        """Get summary of budget stats across all dimensions."""
        return {
            "tokens": {
                "prompt": self.token_budget.prompt_tokens,
                "completion": self.token_budget.completion_tokens,
                "total": self.token_budget.total_tokens,
                "max": self.token_budget.max_tokens,
                "soft_limit": self.token_budget.soft_limit_tokens,
                "utilization": self.token_budget.utilization(),
            },
            "searches": {
                "conducted": self.search_budget.searches_conducted,
                "max": self.search_budget.max_searches,
                "soft_limit": self.search_budget.soft_limit_searches,
                "utilization": self.search_budget.utilization(),
            },
            "tools": {
                "calls": self.tool_budget.tool_calls,
                "max": self.tool_budget.max_tool_calls,
                "soft_limit": self.tool_budget.soft_limit_tool_calls,
                "utilization": self.tool_budget.utilization(),
            },
            "wall_clock": {
                "elapsed_seconds": round(self.wall_clock_budget.elapsed_seconds, 2),
                "max_seconds": self.wall_clock_budget.max_seconds,
                "soft_limit_seconds": self.wall_clock_budget.soft_limit_seconds,
                "utilization": self.wall_clock_budget.utilization(),
            },
        }


class BudgetService:
    """Manager for run and sub-task budget enforcement."""

    def __init__(self):
        self._run_budgets: dict[str, CompositeBudget] = {}
        self._sub_task_budgets: dict[str, dict[str, CompositeBudget]] = {}  # run_id -> {sub_task_id: budget}

    def create_run_budget(
        self,
        run_id: str,
        max_tokens: int = 100_000,
        max_searches: int = 20,
        max_tool_calls: int = 50,
        max_seconds: float = 300.0,
        soft_token_ratio: float = 0.8,
    ) -> CompositeBudget:
        """Create and register a composite budget for a top-level run."""
        budget = CompositeBudget(
            token_budget=TokenBudget(max_tokens=max_tokens, soft_limit_tokens=int(max_tokens * soft_token_ratio)),
            search_budget=SearchBudget(max_searches=max_searches, soft_limit_searches=int(max_searches * soft_token_ratio)),
            tool_budget=ToolBudget(max_tool_calls=max_tool_calls, soft_limit_tool_calls=int(max_tool_calls * soft_token_ratio)),
            wall_clock_budget=WallClockBudget(max_seconds=max_seconds, soft_limit_seconds=max_seconds * soft_token_ratio),
            run_id=run_id,
        )
        self._run_budgets[run_id] = budget
        self._sub_task_budgets[run_id] = {}
        return budget

    def get_run_budget(self, run_id: str) -> Optional[CompositeBudget]:
        return self._run_budgets.get(run_id)

    def create_sub_task_budget(
        self,
        run_id: str,
        sub_task_id: str,
        max_tokens: Optional[int] = None,
        max_searches: Optional[int] = None,
        max_tool_calls: Optional[int] = None,
        max_seconds: Optional[float] = None,
    ) -> CompositeBudget:
        """Create a sub-task budget bounded by parent run budget remaining capacity."""
        parent = self._run_budgets.get(run_id)
        if not parent:
            # Fallback to creating a new parent if not found
            parent = self.create_run_budget(run_id)

        # Default sub-task budget limits to parent remaining or specified limits
        sub_max_tokens = min(max_tokens if max_tokens is not None else parent.token_budget.remaining(), parent.token_budget.remaining())
        sub_max_searches = min(max_searches if max_searches is not None else parent.search_budget.remaining(), parent.search_budget.remaining())
        sub_max_tools = min(max_tool_calls if max_tool_calls is not None else parent.tool_budget.remaining(), parent.tool_budget.remaining())
        sub_max_seconds = min(max_seconds if max_seconds is not None else parent.wall_clock_budget.remaining(), parent.wall_clock_budget.remaining())

        sub_budget = CompositeBudget(
            token_budget=TokenBudget(max_tokens=max(0, sub_max_tokens)),
            search_budget=SearchBudget(max_searches=max(0, sub_max_searches)),
            tool_budget=ToolBudget(max_tool_calls=max(0, sub_max_tools)),
            wall_clock_budget=WallClockBudget(max_seconds=max(0.0, sub_max_seconds)),
            run_id=run_id,
            sub_task_id=sub_task_id,
        )
        if run_id not in self._sub_task_budgets:
            self._sub_task_budgets[run_id] = {}
        self._sub_task_budgets[run_id][sub_task_id] = sub_budget
        return sub_budget

    def get_sub_task_budget(self, run_id: str, sub_task_id: str) -> Optional[CompositeBudget]:
        return self._sub_task_budgets.get(run_id, {}).get(sub_task_id)

    def record_usage(
        self,
        run_id: str,
        sub_task_id: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        searches: int = 0,
        tool_calls: int = 0,
    ) -> list[str]:
        """
        Record usage for run (and sub-task if provided).
        Checks hard and soft limits. Raises BudgetExceededError if hard limit hit.
        Returns soft limit warnings.
        """
        warnings = []
        parent = self._run_budgets.get(run_id)
        if parent:
            parent.token_budget.record_usage(prompt_tokens, completion_tokens)
            parent.search_budget.record_usage(searches)
            parent.tool_budget.record_usage(tool_calls)
            parent_warnings = parent.enforce()
            warnings.extend(parent_warnings)

        if sub_task_id:
            sub_budget = self.get_sub_task_budget(run_id, sub_task_id)
            if sub_budget:
                sub_budget.token_budget.record_usage(prompt_tokens, completion_tokens)
                sub_budget.search_budget.record_usage(searches)
                sub_budget.tool_budget.record_usage(tool_calls)
                sub_warnings = sub_budget.enforce()
                warnings.extend(sub_warnings)

        return warnings

    def update_agent_run_model(self, db_session: Any, agent_run: Any) -> None:
        """
        Update an AgentRun database model instance with current budget stats.
        Updates agent_run.tokens_used, agent_run.elapsed_seconds, and stores stats in execution_log.
        """
        run_id = str(agent_run.id)
        budget = self.get_run_budget(run_id)
        if not budget:
            return

        agent_run.tokens_used = budget.token_budget.total_tokens
        agent_run.elapsed_seconds = budget.wall_clock_budget.elapsed_seconds
        
        exec_log = agent_run.execution_log or {}
        exec_log["budget_stats"] = budget.get_summary()
        agent_run.execution_log = exec_log
        if hasattr(db_session, "add"):
            db_session.add(agent_run)

    def cleanup(self, run_id: str) -> None:
        self._run_budgets.pop(run_id, None)
        self._sub_task_budgets.pop(run_id, None)


# Singleton budget service instance
budget_service = BudgetService()
