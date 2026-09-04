"""Agent Timeline & Gantt Chart Visualization Service.

Tracks execution timelines across parallel agent workstreams, step durations, and tool calls.
Emits SSE real-time telemetry events (`telemetry:agent_timeline_step`).
"""
from datetime import datetime, timezone
import time
from typing import Any, Optional
import logging

from app.schemas.observability import AgentTimelineStep, AgentTimelineResponse
from app.services.stream_service import StreamEvent, stream_service

logger = logging.getLogger(__name__)


class AgentTimelineService:
    """Service managing real-time Gantt timeline steps per run."""

    def __init__(self):
        # In-memory storage: run_id -> list[AgentTimelineStep]
        self._timelines: dict[str, list[dict[str, Any]]] = {}

    def record_step_start(
        self,
        run_id: str,
        agent_name: str,
        step_name: str,
        tool_calls: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Record the start of a new agent execution step in the timeline."""
        run_str = str(run_id)
        if run_str not in self._timelines:
            self._timelines[run_str] = []

        now_dt = datetime.now(timezone.utc)
        step = {
            "agent_name": agent_name,
            "step_name": step_name,
            "start_time": now_dt.isoformat(),
            "start_ts": time.time(),
            "end_time": None,
            "duration_ms": 0.0,
            "tool_calls": tool_calls or [],
            "status": "running",
        }
        self._timelines[run_str].append(step)

        # Broadcast SSE event
        stream_service.publish(
            run_str,
            StreamEvent(
                event_type="telemetry:agent_timeline_step",
                data={
                    "event": "step_started",
                    "agent_name": agent_name,
                    "step_name": step_name,
                    "start_time": step["start_time"],
                    "tool_calls": step["tool_calls"],
                    "status": "running",
                },
                timestamp=datetime.now(timezone.utc),
            ),
        )
        return step

    def record_step_complete(
        self,
        run_id: str,
        agent_name: str,
        step_name: str,
        status: str = "completed",
        tool_calls: Optional[list[str]] = None,
    ) -> Optional[dict[str, Any]]:
        """Record the completion of an agent execution step in the timeline."""
        run_str = str(run_id)
        if run_str not in self._timelines:
            return None

        # Find matching running step
        steps = self._timelines[run_str]
        target_step = None
        for s in reversed(steps):
            if s["agent_name"] == agent_name and s["step_name"] == step_name and s["status"] == "running":
                target_step = s
                break

        if not target_step and steps:
            target_step = steps[-1]

        if target_step:
            now_dt = datetime.now(timezone.utc)
            target_step["end_time"] = now_dt.isoformat()
            target_step["duration_ms"] = round((time.time() - target_step["start_ts"]) * 1000.0, 2)
            target_step["status"] = status
            if tool_calls:
                target_step["tool_calls"] = list(set(target_step["tool_calls"] + tool_calls))

            # Broadcast SSE event
            stream_service.publish(
                run_str,
                StreamEvent(
                    event_type="telemetry:agent_timeline_step",
                    data={
                        "event": "step_completed",
                        "agent_name": agent_name,
                        "step_name": step_name,
                        "duration_ms": target_step["duration_ms"],
                        "status": status,
                        "tool_calls": target_step["tool_calls"],
                    },
                    timestamp=datetime.now(timezone.utc),
                ),
            )
            return target_step

        return None

    def get_timeline(self, run_id: str) -> AgentTimelineResponse:
        """Get the full Gantt chart execution timeline for a run."""
        run_str = str(run_id)
        raw_steps = self._timelines.get(run_str, [])

        schema_steps: list[AgentTimelineStep] = []
        total_duration = 0.0

        for s in raw_steps:
            duration = s.get("duration_ms", 0.0)
            total_duration += duration
            schema_steps.append(
                AgentTimelineStep(
                    agent_name=s["agent_name"],
                    step_name=s["step_name"],
                    start_time=s["start_time"],
                    end_time=s.get("end_time"),
                    duration_ms=duration,
                    tool_calls=s.get("tool_calls", []),
                    status=s.get("status", "completed"),
                )
            )

        return AgentTimelineResponse(
            run_id=run_str,
            total_duration_ms=round(total_duration, 2),
            steps=schema_steps,
        )


# Global singleton instance
agent_timeline_service = AgentTimelineService()
