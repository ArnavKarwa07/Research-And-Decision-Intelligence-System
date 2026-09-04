"""Checkpoint Engine for RADIS Phase 9 Long-Running Research Jobs.

Provides step-level state checkpointing saving run/graph state, claims, sources, and agent outputs to DB/JSON.
Includes state serialization, deserialization, and state restoration logic via `resume_run_from_checkpoint`.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union

logger = logging.getLogger(__name__)


def custom_json_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "to_dict"):
        return obj.to_dict()
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


@dataclass
class Checkpoint:
    """Represents a step-level execution state snapshot for a research run."""
    checkpoint_id: str
    run_id: str
    step_name: str
    step_index: int
    state: Dict[str, Any]
    claims: List[Dict[str, Any]] = field(default_factory=list)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    agent_outputs: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert Checkpoint object to dictionary."""
        return {
            "checkpoint_id": self.checkpoint_id,
            "run_id": self.run_id,
            "step_name": self.step_name,
            "step_index": self.step_index,
            "state": self.state,
            "claims": self.claims,
            "sources": self.sources,
            "agent_outputs": self.agent_outputs,
            "timestamp": self.timestamp,
        }

    def to_json(self) -> str:
        """Serialize Checkpoint to JSON string."""
        return json.dumps(self.to_dict(), default=custom_json_serializer)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Construct Checkpoint from dictionary."""
        return cls(
            checkpoint_id=data.get("checkpoint_id", f"chk-{uuid.uuid4().hex[:8]}"),
            run_id=data.get("run_id", ""),
            step_name=data.get("step_name", "unknown"),
            step_index=data.get("step_index", 0),
            state=data.get("state", {}),
            claims=data.get("claims", []),
            sources=data.get("sources", []),
            agent_outputs=data.get("agent_outputs", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "Checkpoint":
        """Construct Checkpoint from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)


class CheckpointEngine:
    """Engine for persisting and loading run state checkpoints."""

    # In-memory storage for checkpoints: run_id -> List[Checkpoint]
    _checkpoints: Dict[str, List[Checkpoint]] = {}

    @classmethod
    def save_checkpoint(
        cls,
        run_id: str,
        step_name: str,
        state: Dict[str, Any],
        db: Optional[Any] = None,
    ) -> Checkpoint:
        """Save a step-level checkpoint snapshot for a research run."""
        if run_id not in cls._checkpoints:
            cls._checkpoints[run_id] = []

        existing_checkpoints = cls._checkpoints[run_id]
        step_index = len(existing_checkpoints) + 1
        checkpoint_id = f"chk-{run_id[:8] if len(run_id)>=8 else run_id}-{step_index}"

        # Clean/serialize state
        serialized_state = json.loads(json.dumps(state, default=custom_json_serializer))

        # Extract specific state sub-components
        claims = serialized_state.get("claims", [])
        sources = serialized_state.get("scored_sources", []) or serialized_state.get("snippets", [])
        agent_outputs = {
            "decision_matrix": serialized_state.get("decision_matrix"),
            "data_analysis_results": serialized_state.get("data_analysis_results"),
            "visualization_spec": serialized_state.get("visualization_spec"),
            "critique_report": serialized_state.get("critique_report"),
            "hypotheses": serialized_state.get("hypotheses"),
            "falsification_results": serialized_state.get("falsification_results"),
            "summary": serialized_state.get("summary"),
            "confidence": serialized_state.get("confidence"),
        }

        checkpoint = Checkpoint(
            checkpoint_id=checkpoint_id,
            run_id=run_id,
            step_name=step_name,
            step_index=step_index,
            state=serialized_state,
            claims=claims,
            sources=sources,
            agent_outputs=agent_outputs,
        )

        cls._checkpoints[run_id].append(checkpoint)
        logger.info(f"[CheckpointEngine] Saved checkpoint '{checkpoint_id}' for run '{run_id}' at step '{step_name}'")

        # Database persistence if DB session provided
        if db is not None:
            try:
                cls._persist_to_db(db, checkpoint)
            except Exception as e:
                logger.warning(f"[CheckpointEngine] DB persistence warning for run '{run_id}': {e}")

        return checkpoint

    @classmethod
    def _persist_to_db(cls, db: Any, checkpoint: Checkpoint):
        """Helper to persist checkpoint into SQLAlchemy AgentRun execution_log or DB record."""
        # Handles sync or async sessions if needed
        from app.models.agent_run import AgentRun
        import uuid as py_uuid

        try:
            run_uuid = py_uuid.UUID(checkpoint.run_id)
        except (ValueError, AttributeError):
            run_uuid = None

        if run_uuid and hasattr(db, "query"):
            agent_run = db.query(AgentRun).filter(AgentRun.id == run_uuid).first()
            if agent_run:
                log = agent_run.execution_log or {}
                checkpoints_list = log.get("checkpoints", [])
                checkpoints_list.append(checkpoint.to_dict())
                log["checkpoints"] = checkpoints_list
                log["latest_checkpoint_id"] = checkpoint.checkpoint_id
                agent_run.execution_log = log
                db.commit()

    @classmethod
    def get_checkpoints(cls, run_id: str) -> List[Checkpoint]:
        """Retrieve all saved checkpoints for a given run ID."""
        return cls._checkpoints.get(run_id, [])

    @classmethod
    def get_latest_checkpoint(cls, run_id: str) -> Optional[Checkpoint]:
        """Retrieve the latest checkpoint for a given run ID."""
        checkpoints = cls.get_checkpoints(run_id)
        if checkpoints:
            return checkpoints[-1]
        return None

    @classmethod
    def get_checkpoint_by_id(cls, checkpoint_id: str) -> Optional[Checkpoint]:
        """Retrieve a checkpoint by its unique ID across all runs."""
        for run_checkpoints in cls._checkpoints.values():
            for cp in run_checkpoints:
                if cp.checkpoint_id == checkpoint_id:
                    return cp
        return None

    @classmethod
    def clear(cls, run_id: Optional[str] = None):
        """Clear checkpoints for a specific run or all runs."""
        if run_id:
            cls._checkpoints.pop(run_id, None)
        else:
            cls._checkpoints.clear()


def resume_run_from_checkpoint(
    run_id: str,
    checkpoint_id: Optional[str] = None,
    step_name: Optional[str] = None,
    db: Optional[Any] = None,
) -> Dict[str, Any]:
    """State deserialization and resumption logic.

    Retrieves state from checkpoint and reconstructs complete AgentState.
    """
    checkpoint: Optional[Checkpoint] = None

    if checkpoint_id:
        checkpoint = CheckpointEngine.get_checkpoint_by_id(checkpoint_id)
    elif step_name:
        cps = CheckpointEngine.get_checkpoints(run_id)
        for cp in reversed(cps):
            if cp.step_name == step_name:
                checkpoint = cp
                break
    else:
        checkpoint = CheckpointEngine.get_latest_checkpoint(run_id)

    # Fallback to DB if not found in memory engine
    if not checkpoint and db is not None:
        try:
            from app.models.agent_run import AgentRun
            import uuid as py_uuid
            try:
                run_uuid = py_uuid.UUID(run_id)
                agent_run = db.query(AgentRun).filter(AgentRun.id == run_uuid).first()
                if agent_run and agent_run.execution_log:
                    cps_data = agent_run.execution_log.get("checkpoints", [])
                    if cps_data:
                        checkpoint = Checkpoint.from_dict(cps_data[-1])
            except Exception as e:
                logger.warning(f"DB fallback fetch error: {e}")
        except ImportError:
            pass

    if not checkpoint:
        raise ValueError(f"No valid state checkpoint found for run_id '{run_id}'")

    raw_state = checkpoint.state.copy()

    # Reconstruct/Ensure typed AgentState structure
    restored_state: Dict[str, Any] = {
        "query_id": raw_state.get("query_id", run_id),
        "text": raw_state.get("text", ""),
        "mode": raw_state.get("mode", "comprehensive"),
        "plan": raw_state.get("plan", []),
        "steps": raw_state.get("steps", []),
        "snippets": raw_state.get("snippets", []),
        "chunks": raw_state.get("chunks", []),
        "claims": raw_state.get("claims", []),
        "scored_sources": raw_state.get("scored_sources", []),
        "claim_source_links": raw_state.get("claim_source_links", []),
        "contradictions": raw_state.get("contradictions", []),
        "source_groups": raw_state.get("source_groups", []),
        "stale_source_ids": raw_state.get("stale_source_ids", []),
        "fact_check_results": raw_state.get("fact_check_results", []),
        "verification_loop_count": raw_state.get("verification_loop_count", 0),
        "decision_matrix": raw_state.get("decision_matrix"),
        "data_analysis_results": raw_state.get("data_analysis_results"),
        "visualization_spec": raw_state.get("visualization_spec"),
        "search_queries": raw_state.get("search_queries", []),
        "summary": raw_state.get("summary", ""),
        "confidence": raw_state.get("confidence", 0.0),
        "hypotheses": raw_state.get("hypotheses", []),
        "falsification_results": raw_state.get("falsification_results", []),
        "critique_report": raw_state.get("critique_report"),
        "overall_severity": raw_state.get("overall_severity", "LOW"),
        "replan_count": raw_state.get("replan_count", 0),
        "max_replan_iterations": raw_state.get("max_replan_iterations", 3),
        "audit_passed": raw_state.get("audit_passed", True),
        "audit_issues": raw_state.get("audit_issues", []),
        "is_complete": raw_state.get("is_complete", False),
        "current_step": raw_state.get("current_step", checkpoint.step_index),
        "run_id": run_id,
        "checkpoint_id": checkpoint.checkpoint_id,
        "resumed_from_step": checkpoint.step_name,
    }

    logger.info(
        f"[resume_run_from_checkpoint] Resumed run '{run_id}' from checkpoint '{checkpoint.checkpoint_id}' "
        f"at step '{checkpoint.step_name}' with {len(restored_state['claims'])} claims and {len(restored_state['steps'])} steps"
    )
    return restored_state
