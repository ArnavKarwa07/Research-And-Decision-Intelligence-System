"""Evaluation Agent implementing AGENTS.md contract for benchmark quality auditing."""
import time
from typing import Any, Dict, List, Optional
import logging
from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.agent_contracts import EvaluationAgentInput, EvaluationAgentOutput
from app.services.regression_harness_service import RegressionHarnessService

logger = logging.getLogger(__name__)


class EvaluationAgent(BaseAgent):
    """Specialist agent for running benchmark evaluation suites and quality audits."""

    def __init__(self, db_session: Optional[Session] = None):
        super().__init__(
            name="EvaluationAgent",
            role="evaluation",
            description="Evaluates retrieval, claim faithfulness, trajectory efficiency, and decision matrix quality.",
        )
        self.db = db_session

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute evaluation run based on typed EvaluationAgentInput contract."""
        validated_input = EvaluationAgentInput(**input_data)
        start_ts = time.time()

        if not self.db:
            return EvaluationAgentOutput(
                eval_run_id="",
                dataset_id=validated_input.dataset_id,
                overall_score=0.0,
                pass_rate=0.0,
                total_cost_usd=0.0,
                total_latency_ms=0.0,
                summary_message="Database session unavailable for evaluation execution.",
            ).model_dump()

        harness = RegressionHarnessService(self.db)
        eval_run = harness.execute_eval_run(
            dataset_id=validated_input.dataset_id,
            model_name=validated_input.model_name,
            prompt_version=validated_input.prompt_version,
        )

        if not eval_run:
            return EvaluationAgentOutput(
                eval_run_id="",
                dataset_id=validated_input.dataset_id,
                overall_score=0.0,
                pass_rate=0.0,
                total_cost_usd=0.0,
                total_latency_ms=0.0,
                summary_message=f"Evaluation failed: Dataset '{validated_input.dataset_id}' not found.",
            ).model_dump()

        duration_ms = round((time.time() - start_ts) * 1000.0, 2)
        summary = eval_run.summary_metrics or {}

        output = EvaluationAgentOutput(
            eval_run_id=eval_run.id,
            dataset_id=eval_run.dataset_id,
            overall_score=float(summary.get("overall_score", 0.0)),
            pass_rate=float(summary.get("pass_rate", 0.0)),
            total_cost_usd=float(eval_run.total_cost),
            total_latency_ms=duration_ms,
            summary_message=f"Completed evaluation run '{eval_run.id}' with overall score {summary.get('overall_score', 0.0)}.",
            eval_results=[
                {
                    "test_case_id": r.test_case_id,
                    "overall_score": r.overall_score,
                    "pass_status": r.pass_status,
                }
                for r in eval_run.results
            ],
        )

        return output.model_dump()
