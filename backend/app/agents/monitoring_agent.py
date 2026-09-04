"""Monitoring Agent for Continuous Intelligence & Decision Monitoring (Phase 12).

Evaluates research/decision run deltas against baseline snapshots, calculates materiality impact,
generates executive delta summaries, and triggers decision alerts per AGENTS.md rules.
"""
import logging
import uuid
from typing import Any, Dict, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.agents.agent_contracts import MonitoringAgentInput, MonitoringAgentOutput
from app.services.materiality_scoring_engine import MaterialityScoringEngine
from app.services.baseline_delta_service import BaselineDeltaService
from app.services.decision_alerting_service import DecisionAlertingService
from app.services.monitoring_scheduler_service import MonitoringSchedulerService

logger = logging.getLogger(__name__)


class MonitoringAgent(BaseAgent):
    """Specialist agent that evaluates monitoring job run deltas, calculates materiality impact,
    generates executive summaries, and triggers alerts.
    """

    def __init__(self, db_session: Optional[AsyncSession] = None, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                max_steps=5,
                max_tokens=20000,
                timeout_seconds=120,
                allowed_tools=["search_web", "query_database", "compute_delta"],
            )
        super().__init__(config=config, agent_type="monitoring")
        self.db = db_session
        self._output_data: Optional[MonitoringAgentOutput] = None

    async def _audit_tool_call(self, tool_name: str, input_data: Dict[str, Any]) -> Any:
        """Enforce AGENTS.md Rule 9 tool authorization, audit logging, and registry tracking."""
        if tool_name not in self.config.allowed_tools:
            logger.error(f"Agent '{self.state.agent_type}' attempted unauthorized tool call: '{tool_name}'")
            raise PermissionError(f"Agent '{self.state.agent_type}' not allowed to call tool: '{tool_name}'")

        logger.info(
            f"[TOOL_AUDIT] Agent '{self.state.agent_type}' (ID: {self.state.agent_id}) "
            f"invoking tool '{tool_name}' with params: {input_data}"
        )

        if self._tool_registry and hasattr(self._tool_registry, "call"):
            try:
                return await self.call_tool(tool_name, input_data)
            except Exception as exc:
                logger.warning(f"[TOOL_AUDIT] Tool registry call for '{tool_name}' encountered: {exc}")
        return None

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        """Execute step for monitoring delta calculation and materiality analysis."""
        try:
            if isinstance(input_data, MonitoringAgentInput):
                validated_input = input_data
            else:
                validated_input = MonitoringAgentInput(**input_data)
        except Exception as exc:
            logger.error(f"[MonitoringAgent] Input validation error: {exc}")
            self._output_data = MonitoringAgentOutput(
                job_id=str(input_data.get("job_id", "")),
                execution_log_id="",
                status="FAILED",
                materiality_score=0.0,
                materiality_level="NEGLIGIBLE",
                delta_summary={},
                alert_triggered=False,
                stop_reason="INPUT_VALIDATION_FAILED",
                summary_message="Input validation failed.",
                error_message=str(exc),
            )
            return StepResult(
                action="error",
                result=self._output_data.model_dump(),
                tokens_used=10,
                should_continue=False,
                message=f"Validation failed: {exc}",
            )

        job_id_str = validated_input.job_id
        current_state = input_data.get("current_state") or {}

        # 1. DB-backed execution if db_session is present
        if self.db and job_id_str:
            try:
                await self._audit_tool_call("query_database", {"job_id": job_id_str})
                await self._audit_tool_call("compute_delta", {"job_id": job_id_str, "db_backed": True})
                job_uuid = uuid.UUID(job_id_str)
                scheduler = MonitoringSchedulerService(self.db)
                exec_log = await scheduler.execute_job(job_id=job_uuid, current_state=current_state)

                alert_id = None
                if exec_log.alert_triggered:
                    alerting = DecisionAlertingService(self.db)
                    alerts = await alerting.list_alerts(job_id=job_uuid, execution_log_id=exec_log.id)
                    if alerts:
                        alert_id = str(alerts[0].id)

                summary_msg = (
                    f"Monitoring evaluation complete for job '{job_id_str}'. "
                    f"Materiality score: {exec_log.materiality_score:.2f} ({exec_log.materiality_level}). "
                    f"Alert triggered: {exec_log.alert_triggered}."
                )

                self._output_data = MonitoringAgentOutput(
                    job_id=job_id_str,
                    execution_log_id=str(exec_log.id),
                    status=exec_log.status,
                    materiality_score=exec_log.materiality_score,
                    materiality_level=exec_log.materiality_level,
                    delta_summary=exec_log.delta_summary or {},
                    alert_triggered=exec_log.alert_triggered,
                    alert_id=alert_id,
                    stop_reason="OBJECTIVE_SATISFIED",
                    summary_message=summary_msg,
                )

                return StepResult(
                    action="evaluate_delta_db",
                    result=self._output_data.model_dump(),
                    tokens_used=100,
                    should_continue=False,
                    message=summary_msg,
                )
            except Exception as exc:
                logger.error(f"[MonitoringAgent] DB execution error for job {job_id_str}: {exc}", exc_info=True)
                self._output_data = MonitoringAgentOutput(
                    job_id=job_id_str,
                    execution_log_id="",
                    status="FAILED",
                    materiality_score=0.0,
                    materiality_level="NEGLIGIBLE",
                    delta_summary={},
                    alert_triggered=False,
                    stop_reason="EXECUTION_FAILED",
                    summary_message=f"Monitoring execution failed: {exc}",
                    error_message=str(exc),
                )
                return StepResult(
                    action="error",
                    result=self._output_data.model_dump(),
                    tokens_used=10,
                    should_continue=False,
                    message=str(exc),
                )

        # 2. Standalone calculation if no DB session provided
        sub_scores = current_state.get("sub_scores") or {
            "s_assumption": input_data.get("s_assumption", 0.0),
            "s_contradiction": input_data.get("s_contradiction", 0.0),
            "s_matrix": input_data.get("s_matrix", 0.0),
            "s_source": input_data.get("s_source", 0.0),
        }

        await self._audit_tool_call("compute_delta", {"job_id": job_id_str, "sub_scores": sub_scores})

        s_assump = float(sub_scores.get("s_assumption", 0.0))
        s_contra = float(sub_scores.get("s_contradiction", 0.0))
        s_mat = float(sub_scores.get("s_matrix", 0.0))
        s_src = float(sub_scores.get("s_source", 0.0))

        score_breakdown = MaterialityScoringEngine.calculate_materiality_score(
            s_assumption=s_assump,
            s_contradiction=s_contra,
            s_matrix=s_mat,
            s_source=s_src,
        )

        alert_triggered = score_breakdown.total_score >= validated_input.alert_threshold
        status = "ALERT_TRIGGERED" if alert_triggered else ("SUCCESS" if score_breakdown.total_score > 0 else "NO_CHANGE")

        delta_summary = {
            "breakdown": score_breakdown.model_dump(),
            "diffs": current_state.get("diffs", {}),
            "recommendation_flipped": current_state.get("recommendation_flipped", False),
        }

        summary_msg = (
            f"Standalone monitoring check completed for job '{job_id_str}'. "
            f"Materiality score: {score_breakdown.total_score:.2f} ({score_breakdown.materiality_level}). "
            f"Alert triggered: {alert_triggered}."
        )

        self._output_data = MonitoringAgentOutput(
            job_id=job_id_str,
            execution_log_id=str(uuid.uuid4()),
            status=status,
            materiality_score=score_breakdown.total_score,
            materiality_level=score_breakdown.materiality_level,
            delta_summary=delta_summary,
            alert_triggered=alert_triggered,
            alert_id=str(uuid.uuid4()) if alert_triggered else None,
            stop_reason="OBJECTIVE_SATISFIED",
            summary_message=summary_msg,
        )

        return StepResult(
            action="evaluate_delta_standalone",
            result=self._output_data.model_dump(),
            tokens_used=50,
            should_continue=False,
            message=summary_msg,
        )

    async def compile_output(self) -> Dict[str, Any]:
        """Compile final output after steps."""
        if not self._output_data:
            self._output_data = MonitoringAgentOutput(
                job_id="",
                execution_log_id="",
                status="NO_CHANGE",
                materiality_score=0.0,
                materiality_level="NEGLIGIBLE",
                stop_reason="OBJECTIVE_SATISFIED",
                summary_message="No evaluation steps performed.",
            )
        return self._output_data.model_dump()

    async def execute(self, input_data: Union[Dict[str, Any], MonitoringAgentInput]) -> Dict[str, Any]:
        """Direct execution interface returning MonitoringAgentOutput dictionary."""
        if isinstance(input_data, MonitoringAgentInput):
            inp_dict = input_data.model_dump()
        else:
            inp_dict = dict(input_data)
        await self.run(inp_dict)
        return await self.compile_output()
