"""Cost Telemetry Service for Dynamic Token and Tool Cost Estimation and Real-time SSE Streaming.

Tracks cost metrics after LLM/tool calls and streams telemetry events via stream_service.py.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID, uuid4, NAMESPACE_DNS, uuid5
import logging

from app.services.stream_service import StreamEvent, stream_service

logger = logging.getLogger(__name__)

# Default LLM Pricing table (per 1,000 tokens)
DEFAULT_MODEL_PRICING: dict[str, dict[str, float]] = {
    "gpt-4o": {"prompt": 0.0025, "completion": 0.0100},
    "gpt-4o-mini": {"prompt": 0.00015, "completion": 0.0006},
    "claude-3-5-sonnet": {"prompt": 0.0030, "completion": 0.0150},
    "gemini-1.5-pro": {"prompt": 0.00125, "completion": 0.0050},
    "gemini-1.5-flash": {"prompt": 0.000075, "completion": 0.0003},
    "default": {"prompt": 0.0020, "completion": 0.0080},
}

# Default Tool Call Pricing table (per call USD)
DEFAULT_TOOL_PRICING: dict[str, float] = {
    "web_search": 0.01,
    "tavily_search": 0.01,
    "serper_search": 0.01,
    "python_interpreter": 0.005,
    "code_executor": 0.005,
    "data_agent": 0.002,
    "fact_checker": 0.002,
    "default": 0.001,
}


def _normalize_query_id(query_id: Union[UUID, str]) -> UUID:
    """Ensure query_id is a valid UUID instance."""
    if isinstance(query_id, UUID):
        return query_id
    try:
        return UUID(str(query_id))
    except ValueError:
        return uuid5(NAMESPACE_DNS, str(query_id))


def estimate_llm_cost(
    model_name: str,
    prompt_tokens: int,
    completion_tokens: int,
    custom_pricing: Optional[dict[str, dict[str, float]]] = None,
) -> float:
    """
    Calculate estimated USD cost for an LLM generation call.
    Pricing is computed per 1,000 tokens.
    """
    pricing_map = custom_pricing or DEFAULT_MODEL_PRICING
    model_pricing = pricing_map.get(model_name, pricing_map.get("default", DEFAULT_MODEL_PRICING["default"]))
    prompt_cost = (prompt_tokens / 1000.0) * model_pricing.get("prompt", 0.0020)
    completion_cost = (completion_tokens / 1000.0) * model_pricing.get("completion", 0.0080)
    return round(prompt_cost + completion_cost, 6)


def estimate_tool_cost(
    tool_name: str,
    call_count: int = 1,
    custom_pricing: Optional[dict[str, float]] = None,
) -> float:
    """
    Calculate estimated USD cost for tool calls.
    """
    pricing_map = custom_pricing or DEFAULT_TOOL_PRICING
    unit_cost = pricing_map.get(tool_name, pricing_map.get("default", DEFAULT_TOOL_PRICING["default"]))
    return round(unit_cost * call_count, 6)


@dataclass
class QueryCostMetrics:
    """Cost and token usage breakdown for a single query."""
    query_id: UUID
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    tool_calls: int = 0
    llm_cost: float = 0.0
    tool_cost: float = 0.0
    total_cost: float = 0.0
    cost_by_model: dict[str, float] = field(default_factory=dict)
    cost_by_tool: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": str(self.query_id),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "tool_calls": self.tool_calls,
            "llm_cost": round(self.llm_cost, 6),
            "tool_cost": round(self.tool_cost, 6),
            "total_cost": round(self.total_cost, 6),
            "cost_by_model": {k: round(v, 6) for k, v in self.cost_by_model.items()},
            "cost_by_tool": {k: round(v, 6) for k, v in self.cost_by_tool.items()},
        }


# Telemetry SSE event emission helpers
def emit_cost_updated(query_id: Union[UUID, str], cost_data: dict[str, Any]) -> None:
    """Publish cost update SSE event."""
    norm_id = _normalize_query_id(query_id)
    stream_service.publish(
        norm_id,
        StreamEvent(event_type="telemetry:cost_updated", data=cost_data, timestamp=datetime.now()),
    )


def emit_budget_telemetry(query_id: Union[UUID, str], telemetry_data: dict[str, Any]) -> None:
    """Publish general budget telemetry SSE event."""
    norm_id = _normalize_query_id(query_id)
    stream_service.publish(
        norm_id,
        StreamEvent(event_type="telemetry:budget_updated", data=telemetry_data, timestamp=datetime.now()),
    )


def emit_budget_warning(query_id: Union[UUID, str], warning_data: dict[str, Any]) -> None:
    """Publish budget soft limit warning SSE event."""
    norm_id = _normalize_query_id(query_id)
    stream_service.publish(
        norm_id,
        StreamEvent(event_type="telemetry:budget_warning", data=warning_data, timestamp=datetime.now()),
    )


def emit_budget_exceeded(query_id: Union[UUID, str], error_data: dict[str, Any]) -> None:
    """Publish budget hard limit exceeded SSE event."""
    norm_id = _normalize_query_id(query_id)
    stream_service.publish(
        norm_id,
        StreamEvent(event_type="telemetry:budget_exceeded", data=error_data, timestamp=datetime.now()),
    )


class CostTelemetryTracker:
    """Tracker for accumulating model and tool costs per query and streaming real-time SSE updates."""

    def __init__(self):
        self._metrics: dict[UUID, QueryCostMetrics] = {}

    def get_or_create_metrics(self, query_id: Union[UUID, str]) -> QueryCostMetrics:
        norm_id = _normalize_query_id(query_id)
        if norm_id not in self._metrics:
            self._metrics[norm_id] = QueryCostMetrics(query_id=norm_id)
        return self._metrics[norm_id]

    def record_llm_call(
        self,
        query_id: Union[UUID, str],
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int,
        custom_pricing: Optional[dict] = None,
    ) -> float:
        """
        Record an LLM call, update cost metrics, and stream cost update SSE event.
        Returns the incremental cost for this call.
        """
        norm_id = _normalize_query_id(query_id)
        metrics = self.get_or_create_metrics(norm_id)

        incremental_cost = estimate_llm_cost(model_name, prompt_tokens, completion_tokens, custom_pricing)

        metrics.prompt_tokens += prompt_tokens
        metrics.completion_tokens += completion_tokens
        metrics.total_tokens += prompt_tokens + completion_tokens
        metrics.llm_cost += incremental_cost
        metrics.total_cost += incremental_cost

        metrics.cost_by_model[model_name] = metrics.cost_by_model.get(model_name, 0.0) + incremental_cost

        # Stream update via SSE
        emit_cost_updated(
            norm_id,
            {
                "event": "llm_call",
                "model": model_name,
                "incremental_cost": incremental_cost,
                "summary": metrics.to_dict(),
            },
        )
        return incremental_cost

    def record_tool_call(
        self,
        query_id: Union[UUID, str],
        tool_name: str,
        call_count: int = 1,
        custom_pricing: Optional[dict] = None,
    ) -> float:
        """
        Record tool call(s), update cost metrics, and stream cost update SSE event.
        Returns the incremental cost for this call.
        """
        norm_id = _normalize_query_id(query_id)
        metrics = self.get_or_create_metrics(norm_id)

        incremental_cost = estimate_tool_cost(tool_name, call_count, custom_pricing)

        metrics.tool_calls += call_count
        metrics.tool_cost += incremental_cost
        metrics.total_cost += incremental_cost

        metrics.cost_by_tool[tool_name] = metrics.cost_by_tool.get(tool_name, 0.0) + incremental_cost

        # Stream update via SSE
        emit_cost_updated(
            norm_id,
            {
                "event": "tool_call",
                "tool": tool_name,
                "call_count": call_count,
                "incremental_cost": incremental_cost,
                "summary": metrics.to_dict(),
            },
        )
        return incremental_cost

    def get_summary(self, query_id: Union[UUID, str]) -> dict[str, Any]:
        """Retrieve cost summary dictionary for a query."""
        norm_id = _normalize_query_id(query_id)
        metrics = self.get_or_create_metrics(norm_id)
        return metrics.to_dict()

    def reset(self, query_id: Optional[Union[UUID, str]] = None) -> None:
        """Reset cost metrics."""
        if query_id:
            norm_id = _normalize_query_id(query_id)
            self._metrics.pop(norm_id, None)
        else:
            self._metrics.clear()


# Default singleton instance
cost_telemetry_tracker = CostTelemetryTracker()
