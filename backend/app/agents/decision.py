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
                if hasattr(alt, "model_dump"):
                    alt_copy = alt.model_dump()
                elif hasattr(alt, "dict"):
                    alt_copy = alt.dict()
                elif isinstance(alt, dict):
                    alt_copy = dict(alt)
                else:
                    alt_copy = {"name": str(alt)}

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

            query_topic = input_data.get("query_text") or input_data.get("topic") or input_data.get("objective") or "Target Decision Objective"
            clean_top = str(query_topic).strip()
            short_top = clean_top[:45] + "..." if len(clean_top) > 45 else clean_top

            claims = input_data.get("claims") or []
            snippets = input_data.get("snippets") or []
            contradictions = input_data.get("contradictions") or []
            hypotheses = input_data.get("hypotheses") or []

            # Extract clean sentences across evidence items for dynamic grounding
            extracted_sentences: List[str] = []
            raw_items = (claims or []) + (snippets or [])
            for item in raw_items:
                content = ""
                if isinstance(item, dict):
                    content = item.get("snippet") or item.get("content") or item.get("description") or ""
                elif isinstance(item, str):
                    content = item
                else:
                    content = str(item)
                if content and len(content) > 15:
                    import re
                    sents = [s.strip() for s in re.split(r'[.!?]\s+', str(content)) if len(s.strip()) > 15]
                    extracted_sentences.extend(sents)

            unique_sents: List[str] = []
            for s in extracted_sentences:
                if s not in unique_sents:
                    unique_sents.append(s)

            # Dynamically extract risks from input claims, contradictions, or snippet sentences
            if "risks" in input_data and input_data["risks"]:
                self.risks = input_data["risks"]
            else:
                extracted_risks = []
                for contra in contradictions:
                    c_desc = contra.get("description") if isinstance(contra, dict) else str(contra)
                    if c_desc:
                        extracted_risks.append(f"Evidence contradiction: {c_desc[:120]}")

                for c in claims:
                    if isinstance(c, dict):
                        conf = float(c.get("confidence", 1.0))
                        content = c.get("content", "")
                        status = c.get("support_status", "SUPPORTED")
                        if conf < 0.85 or status != "SUPPORTED" or any(kw in content.lower() for kw in ["risk", "latency", "cost", "challenge", "bottleneck", "uncertainty"]):
                            extracted_risks.append(f"Uncertainty in claim: '{content[:120]}'")

                for h in hypotheses:
                    if isinstance(h, dict) and h.get("vulnerabilities"):
                        for vul in h["vulnerabilities"][:2]:
                            extracted_risks.append(f"Hypothesis vulnerability: {vul[:120]}")

                if not extracted_risks and unique_sents:
                    for s in unique_sents:
                        if any(kw in s.lower() for kw in ["risk", "cost", "delay", "challenge", "bottleneck", "limit", "overhead"]):
                            extracted_risks.append(f"Grounding risk: {s}")

                if not extracted_risks:
                    s_ref = unique_sents[0] if unique_sents else f"Operational execution parameters for '{clean_top}'"
                    extracted_risks = [
                        f"Operational friction and implementation complexity: {s_ref[:100]}",
                        f"Resource allocation constraints and scheduling variance during deployment of '{short_top}'",
                        f"External requirement shifts or environment changes for '{short_top}'"
                    ]
                self.risks = extracted_risks[:5]

            # Dynamically extract assumptions from claims, evidence, or snippet sentences
            if "assumptions" in input_data and input_data["assumptions"]:
                self.assumptions = input_data["assumptions"]
            else:
                extracted_assumptions = []
                for c in claims:
                    if isinstance(c, dict) and float(c.get("confidence", 0.0)) >= 0.85:
                        c_text = c.get("content", "")
                        if c_text and len(c_text) > 10:
                            extracted_assumptions.append(f"Assumes verified claim holds: '{c_text[:120]}'")

                if not extracted_assumptions and unique_sents:
                    for s in unique_sents[:3]:
                        extracted_assumptions.append(f"Assumes empirical finding: '{s[:120]}'")

                if not extracted_assumptions:
                    extracted_assumptions = [
                        f"Assumes evaluation criteria weights accurately reflect priority focus for '{short_top}'",
                        f"Assumes baseline research evidence and domain parameters remain stable for '{short_top}'",
                        f"Assumes execution team and resources remain available as scheduled"
                    ]
                self.assumptions = extracted_assumptions[:5]

            # Dynamically extract/construct decision triggers from claims/alternatives/topic
            if "decision_triggers" in input_data and input_data["decision_triggers"]:
                self.triggers = input_data["decision_triggers"]
            elif "triggers" in input_data and input_data["triggers"]:
                self.triggers = input_data["triggers"]
            else:
                s_trigger = unique_sents[0] if unique_sents else f"Primary domain evidence for '{short_top}'"
                extracted_triggers = [
                    {
                        "condition": f"Confidence score for evidence ('{s_trigger[:60]}...') drops below 75%",
                        "threshold": "< 75% confidence",
                        "action": "Trigger immediate re-evaluation and pivot to secondary fallback option",
                        "severity": "high"
                    },
                    {
                        "condition": f"Key criteria weight shift or operational variance for '{short_top}' > 15%",
                        "threshold": "> 15%",
                        "action": "Re-run multi-criteria sensitivity matrix and trade-off scoring",
                        "severity": "medium"
                    }
                ]
                if contradictions:
                    extracted_triggers.append({
                        "condition": f"Critical contradiction detected in active evidence stream for '{short_top}'",
                        "threshold": "Critical Severity",
                        "action": "Pause execution pipeline and initiate red-team audit pass",
                        "severity": "critical"
                    })
                self.triggers = extracted_triggers

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
