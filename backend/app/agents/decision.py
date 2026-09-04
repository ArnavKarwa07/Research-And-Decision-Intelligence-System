"""Decision Agent for Decision Intelligence.

Compares alternatives against evaluation criteria using multi-criteria weighted scoring,
simulates best/base/worst scenarios, executes weight sensitivity stress-testing,
calculates expected values, and identifies decision triggers.
"""
from typing import Any, Dict, List, Optional
import logging

from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.agents.agent_contracts import (
    AlternativeOption,
    DecisionMatrix,
)
from app.tools.decision_tools import (
    compare_options,
    run_scenario,
    run_sensitivity,
    calculate_expected_value,
)

logger = logging.getLogger(__name__)


class DecisionAgent(BaseAgent):
    """Specialist agent that performs multi-criteria decision analysis, scenario simulation, and sensitivity stress-testing."""

    def __init__(self, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                max_steps=5,
                max_tokens=40000,
                timeout_seconds=60,
                allowed_tools=[
                    "compare_options",
                    "run_scenario",
                    "run_sensitivity",
                    "calculate_expected_value",
                ]
            )
        super().__init__(config=config, agent_type="decision")
        self.decision_matrix_result: Optional[Dict[str, Any]] = None
        self.scenario_result: Optional[Dict[str, Any]] = None
        self.sensitivity_result: Optional[Dict[str, Any]] = None
        self.expected_value_result: Optional[Dict[str, Any]] = None
        self.risks: List[str] = []
        self.assumptions: List[str] = []
        self.triggers: List[Dict[str, Any]] = []

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        step_num = self.state.steps_taken

        if step_num == 0:
            # Step 1: Multi-Criteria Decision Analysis (compare_options)
            alternatives = input_data.get("alternatives", [])
            criteria = input_data.get("criteria", [])

            if not alternatives or not criteria:
                raise ValueError("At least one alternative and one criterion are required for decision analysis.")

            # Ensure every alternative has a 'scores' dict covering all criteria.
            # If scores are missing for a criterion, default to 0.5 (neutral).
            criteria_ids = [str(c.get("id", c.get("name", ""))) for c in criteria]
            criteria_names = [str(c.get("name", c.get("id", ""))) for c in criteria]
            enriched_alternatives = []
            for alt in alternatives:
                alt_copy = dict(alt)
                scores = dict(alt_copy.get("scores") or {})
                for cid, cname in zip(criteria_ids, criteria_names):
                    if cid not in scores and cname not in scores:
                        scores[cid] = 0.5
                alt_copy["scores"] = scores
                enriched_alternatives.append(alt_copy)

            self.decision_matrix_result = compare_options(enriched_alternatives, criteria)
            msg = f"Completed weighted scoring matrix for {len(alternatives)} options."

            return StepResult(
                action="compare_options",
                result=self.decision_matrix_result,
                tokens_used=150,
                should_continue=True,
                message=msg
            )

        elif step_num == 1:
            # Step 2: Scenario Analysis (run_scenario)
            alternatives = self.decision_matrix_result.get("ranked_alternatives", []) if self.decision_matrix_result else []
            raw_scenarios = input_data.get("scenarios")
            if raw_scenarios:
                scenarios = raw_scenarios
            else:
                scenarios = [
                    {"name": "Best Case", "probability": 0.25, "description": "Ideal economic & operational conditions"},
                    {"name": "Base Case", "probability": 0.50, "description": "Expected baseline performance"},
                    {"name": "Worst Case", "probability": 0.25, "description": "Downside risks materialize"}
                ]

            self.scenario_result = run_scenario(alternatives, scenarios)
            msg = f"Evaluated scenarios across {len(scenarios)} states."

            return StepResult(
                action="run_scenario",
                result=self.scenario_result,
                tokens_used=150,
                should_continue=True,
                message=msg
            )

        elif step_num == 2:
            # Step 3: Sensitivity Stress-Testing (run_sensitivity)
            alternatives = self.decision_matrix_result.get("ranked_alternatives", []) if self.decision_matrix_result else []
            criteria = self.decision_matrix_result.get("criteria", []) if self.decision_matrix_result else []

            self.sensitivity_result = run_sensitivity(alternatives, criteria)
            msg = f"Sensitivity analysis found {len(self.sensitivity_result.get('switch_points', []))} tipping points."

            return StepResult(
                action="run_sensitivity",
                result=self.sensitivity_result,
                tokens_used=150,
                should_continue=True,
                message=msg
            )

        elif step_num == 3:
            # Step 4: Expected Value & Triggers Identification
            scenarios_list = self.scenario_result.get("scenarios", []) if self.scenario_result else []
            if scenarios_list:
                try:
                    self.expected_value_result = calculate_expected_value(scenarios_list)
                except Exception as e:
                    logger.warning(f"Expected value calculation fallback: {e}")
                    self.expected_value_result = {"expected_values": {}, "best_ev_alternative": ""}
            else:
                self.expected_value_result = {"expected_values": {}, "best_ev_alternative": ""}

            self.risks = input_data.get("risks", [
                "Uncertain market adoption rate",
                "Vendor dependencies and potential lock-in",
                "Resource constraints during initial deployment"
            ])
            self.assumptions = input_data.get("assumptions", [
                "Criteria weights accurately reflect user priorities",
                "Baseline cost estimations hold within +/- 15% margin",
                "No major regulatory shifts occur within planning horizon"
            ])
            self.triggers = input_data.get("decision_triggers", [
                {
                    "condition": "Cost overrun exceeds 20% threshold",
                    "threshold": "> 20%",
                    "action": "Trigger immediate re-evaluation and switch to Option B",
                    "severity": "high"
                },
                {
                    "condition": "Key criteria weight shift > 15%",
                    "threshold": "> 15%",
                    "action": "Re-run sensitivity matrix",
                    "severity": "medium"
                }
            ])

            return StepResult(
                action="finalize_decision",
                result={"expected_values": self.expected_value_result, "triggers": self.triggers},
                tokens_used=100,
                should_continue=False,
                message="Finalized decision analysis, expected values, and decision triggers."
            )

        return StepResult(
            action="done",
            result=None,
            tokens_used=0,
            should_continue=False,
            message="Decision agent finished."
        )

    async def compile_output(self) -> Dict[str, Any]:
        dm = self.decision_matrix_result or {}
        rec = dm.get("recommendation", "Option A")
        conf = dm.get("confidence", 0.80)

        raw_alts = dm.get("ranked_alternatives", [])
        alt_options = []
        for alt in raw_alts:
            if isinstance(alt, dict):
                alt_options.append(
                    AlternativeOption(
                        name=alt.get("name", "Option"),
                        pros=alt.get("pros", ["Fulfills core criteria"]),
                        cons=alt.get("cons", ["Requires resource allocation"]),
                        score=alt.get("weighted_score", 0.75)
                    )
                )

        rationale = (
            f"Primary recommendation '{rec}' selected based on highest weighted multi-criteria score "
            f"({conf * 100:.1f}% confidence). Supported by best/base/worst scenario projections and "
            f"sensitivity analysis of criteria weights."
        )

        trigger_conditions = []
        for t in self.triggers:
            if isinstance(t, dict):
                cond = t.get("condition") or t.get("name") or str(t)
                trigger_conditions.append(cond)
            else:
                trigger_conditions.append(str(t))

        matrix = DecisionMatrix(
            recommendation=rec,
            confidence=conf,
            rationale=rationale,
            alternatives=alt_options,
            key_risks=self.risks,
            assumptions=self.assumptions,
            decision_triggers=trigger_conditions
        )

        return {
            "recommendation": rec,
            "confidence": conf,
            "rationale": rationale,
            "decision_matrix": matrix.model_dump(),
            "weighted_matrix": dm.get("weighted_matrix", {}),
            "criteria": dm.get("criteria", []),
            "alternatives": dm.get("ranked_alternatives", []),
            "scenarios": self.scenario_result or {},
            "sensitivity_analysis": self.sensitivity_result or {},
            "expected_values": self.expected_value_result or {},
            "key_risks": self.risks,
            "assumptions": self.assumptions,
            "decision_triggers": self.triggers
        }
