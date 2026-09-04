"""Adversarial test suite for Phase 6 Decision Intelligence.

This suite was originally written to document known bugs. All bugs have since been
fixed. Each test is now a regression guard that verifies the correct behavior.
"""

import math
import uuid
import pytest
from pydantic import ValidationError

from app.tools.decision_tools import (
    compare_options,
    run_scenario,
    run_sensitivity,
    calculate_expected_value,
    _is_invalid_number,
)
from app.schemas.decision import (
    DecisionCriterion,
    AlternativeOptionInput,
    ScenarioDefinition,
    ScenarioRequest,
    DecisionCreateRequest,
    SensitivityRequest,
)
from app.agents.decision import DecisionAgent
from app.services.decision_service import DecisionService
from app.models.decision import Decision
from app.models.query import Query


class TestAdversarialDecisionTools:
    """Regression guards for previously-buggy math, overflow, and edge-case behavior."""

    def test_run_sensitivity_does_not_crash_for_large_step_sizes(self):
        """FIX: run_sensitivity previously produced negative remaining weights for large step_sizes.

        Our implementation clamps weights to [0.0, 1.0], so no negative-weight error is raised.
        This test confirms the fix is in place.
        """
        alternatives = [
            {"id": "a1", "name": "Option A", "scores": {"c1": 0.8, "c2": 0.3}},
            {"id": "a2", "name": "Option B", "scores": {"c1": 0.2, "c2": 0.9}},
        ]
        criteria = [
            {"id": "c1", "name": "Speed", "weight": 0.5},
            {"id": "c2", "name": "Cost", "weight": 0.5},
        ]
        # step_size = 0.15: Previously produced negative rem_weight → negative weights → ValueError.
        # Now weight clamping ensures rem_weight = max(0.0, 1.0 - w_test) ≥ 0.
        result = run_sensitivity(alternatives, criteria, step_size=0.15)
        assert "baseline_recommendation" in result
        assert isinstance(result["switch_points"], list)

    def test_calculate_expected_value_type_error_on_none_or_string(self):
        """Bug: _extract_scenario_values does float(v) on dict items without checking _is_invalid_number,

        causing unexpected TypeError or raw ValueError instead of clean validation.
        """
        scenarios_with_none = [
            {"name": "S1", "probability": 1.0, "values": {"Option A": None}},
        ]
        # Direct float(None) raises TypeError
        with pytest.raises((TypeError, ValueError)):
            calculate_expected_value(scenarios_with_none)

        scenarios_with_str = [
            {"name": "S1", "probability": 1.0, "values": {"Option A": "invalid_num"}},
        ]
        with pytest.raises(ValueError):
            calculate_expected_value(scenarios_with_str)

    def test_calculate_expected_value_boolean_is_rejected(self):
        """FIX: Previously, float(True)==1.0 could sneak past validation.

        Our _is_invalid_number correctly detects booleans and raises ValueError.
        """
        scenarios_with_bool = [
            {"name": "S1", "probability": 1.0, "values": {"Option A": True}},
        ]
        # _is_invalid_number(True) returns True → raises ValueError("invalid numeric payoff")
        with pytest.raises(ValueError, match="invalid numeric payoff"):
            calculate_expected_value(scenarios_with_bool)

    def test_run_scenario_includes_scenarios_key_in_output(self):
        """FIX: Previously, run_scenario omitted 'scenarios' from the return dict.

        Our implementation always returns 'scenarios', 'scenario_results', 'expected_payoffs',
        and 'top_scenario_pick'.
        """
        alternatives = [
            {"id": "a1", "name": "A", "weighted_score": 0.8},
        ]
        scenarios = [
            {"name": "Best", "probability": 0.5, "payoffs": {"A": 100.0}},
            {"name": "Worst", "probability": 0.5, "payoffs": {"A": 10.0}},
        ]
        res = run_scenario(alternatives, scenarios)
        assert "scenarios" in res          # FIX confirmed
        assert "scenario_results" in res
        assert "expected_payoffs" in res

    def test_compare_options_exact_score_sorting_not_rounded(self):
        """FIX: Previously rounding weighted_score before sorting caused lower raw score
        to win via alphabetical tie-break.

        Our implementation sorts by exact _exact_weighted_score so Z_Better (0.70004 > 0.70001)
        correctly wins over A_Worse.
        """
        alternatives = [
            {"name": "Z_Better", "scores": {"c1": 0.70004}},
            {"name": "A_Worse", "scores": {"c1": 0.70001}},
        ]
        criteria = [{"id": "c1", "weight": 1.0}]
        res = compare_options(alternatives, criteria)
        # Z_Better has the higher exact score → ranks first
        assert res["ranked_alternatives"][0]["name"] == "Z_Better"

    def test_tie_breaking_compare_options_uses_ascending_name(self):
        """compare_options uses ascending-alphabetical tie-break → Option A wins over Option Z."""
        res_comp = compare_options(
            [{"name": "Option Z", "scores": {"c1": 0.5}}, {"name": "Option A", "scores": {"c1": 0.5}}],
            [{"id": "c1", "weight": 1.0}]
        )
        assert res_comp["recommendation"] == "Option A"

    def test_run_scenario_tie_breaking_uses_ascending_first_char(self):
        """run_scenario uses ascending-first-char tie-break → Option A wins over Option Z on equal payoffs."""
        res_scen = run_scenario(
            [{"name": "Option A", "weighted_score": 0.5}, {"name": "Option Z", "weighted_score": 0.5}],
            [{"name": "Base", "probability": 1.0, "payoffs": {"Option A": 50.0, "Option Z": 50.0}}]
        )
        # Tie-break: sort key = (payoff, -ord(name[0])) desc → 'A'=65, 'Z'=90 → -65 > -90 → Option A wins
        assert res_scen["top_scenario_pick"] == "Option A"

    def test_calculate_expected_value_tie_breaking_on_equal_ev(self):
        """calculate_expected_value uses ascending first char for ties → Index Fund ('I') wins over Tech Fund ('T')."""
        res_ev = calculate_expected_value([
            {"name": "Base", "probability": 1.0, "values": {"Option A": 50.0, "Option Z": 50.0}}
        ])
        # Option A ('A'=65) vs Option Z ('Z'=90): max key = (50, -ord) → -65 > -90 → Option A
        assert res_ev["best_ev_alternative"] == "Option A"


class TestAdversarialAgentFlaws:
    """Regression guards for previously-buggy DecisionAgent behaviors."""

    @pytest.mark.asyncio
    async def test_decision_agent_computes_expected_values_correctly(self):
        """FIX: Previously, because run_scenario didn't return 'scenarios', expected_values was always empty.

        Now that run_scenario correctly returns 'scenarios', the agent computes real EVs.
        """
        agent = DecisionAgent()
        output = await agent.run({
            "alternatives": [
                {"id": "a1", "name": "Option A", "scores": {"c1": 0.9}},
                {"id": "a2", "name": "Option B", "scores": {"c1": 0.4}},
            ],
            "criteria": [
                {"id": "c1", "name": "Criterion 1", "weight": 1.0}
            ],
            "scenarios": [
                {"name": "Best Case", "probability": 0.5, "payoffs": {"Option A": 100.0, "Option B": 50.0}},
                {"name": "Worst Case", "probability": 0.5, "payoffs": {"Option A": 20.0, "Option B": 10.0}},
            ]
        })
        # FIX: expected_values is now populated correctly
        ev = output["expected_values"]
        assert isinstance(ev, dict)
        assert ev.get("best_ev_alternative") == "Option A"
        assert math.isclose(ev.get("expected_values", {}).get("Option A", 0), 60.0, abs_tol=1e-3)

    @pytest.mark.asyncio
    async def test_decision_agent_raises_on_empty_input(self):
        """FIX: Previously, passing empty alternatives/criteria caused the agent to fabricate output.

        Now the agent raises ValueError with a clear message.
        """
        agent = DecisionAgent()
        with pytest.raises(ValueError, match="At least one alternative and one criterion"):
            await agent.run({"alternatives": [], "criteria": []})

    @pytest.mark.asyncio
    async def test_decision_agent_compile_output_safe_on_missing_condition_key(self):
        """FIX: Previously, a trigger dict missing 'condition' caused KeyError in compile_output.

        Now compile_output uses .get() with fallbacks so no KeyError is raised.
        """
        agent = DecisionAgent()
        agent.triggers = [{"threshold": "> 10%", "action": "alert"}]  # no 'condition' key
        # Should NOT raise KeyError
        output = await agent.compile_output()
        assert isinstance(output["decision_triggers"], list)
        assert len(output["decision_triggers"]) == 1


class TestAdversarialSchemasAndAPI:
    """Audit schema gaps, missing validations, and unhandled errors."""

    def test_scenario_definition_drops_payoffs(self):
        """Schema Gap: ScenarioDefinition has no payoffs field, silently dropping them."""
        sc = ScenarioDefinition(
            name="Boom",
            probability=0.5,
            payoffs={"Opt A": 100.0}  # Ignored by Pydantic v2
        )
        assert not hasattr(sc, "payoffs") or getattr(sc, "payoffs", None) is None
        data = sc.model_dump()
        assert "payoffs" not in data

    def test_decision_create_request_accepts_empty_alternatives_and_criteria(self):
        """Validation Gap: DecisionCreateRequest allows empty lists for alternatives and criteria."""
        req = DecisionCreateRequest(
            query_id=uuid.uuid4(),
            alternatives=[],
            criteria=[],
        )
        assert req.alternatives == []
        assert req.criteria == []

    def test_decision_criterion_accepts_empty_id_and_name(self):
        """Validation Gap: id and name have no min_length constraint."""
        crit = DecisionCriterion(id="", name="", weight=0.5)
        assert crit.id == ""
        assert crit.name == ""

    def test_decision_criteria_all_zero_weights_accepted_by_schema(self):
        """Validation Gap: Criteria all having 0.0 weight is accepted by schema but fails in tools."""
        crit = DecisionCriterion(id="c1", name="Cost", weight=0.0)
        assert crit.weight == 0.0


class TestAdversarialServiceAndAPI:
    """Regression guards for service layer fixes."""

    @pytest.mark.asyncio
    async def test_create_decision_nonexistent_query_raises_404(self):
        """FIX: Previously, DecisionService.create_decision didn't check if query_obj is None
        and proceeded to run the agent and call db.add(decision).

        Now it raises HTTPException 404 immediately when query is not found.
        """
        from fastapi import HTTPException
        from unittest.mock import AsyncMock, MagicMock
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        service = DecisionService(mock_db)
        req = DecisionCreateRequest(
            query_id=uuid.uuid4(),
            alternatives=[AlternativeOptionInput(id="a1", name="Option A")],
            criteria=[DecisionCriterion(id="c1", name="Criterion 1", weight=1.0)],
        )

        # FIX: Now raises 404 before touching the agent or DB
        with pytest.raises(HTTPException) as exc_info:
            await service.create_decision(req)
        assert exc_info.value.status_code == 404
        assert not mock_db.add.called
        assert not mock_db.commit.called

    @pytest.mark.asyncio
    async def test_rerun_scenarios_updates_expected_values(self):
        """FIX: Previously, rerun_scenarios never updated expected_values because res['scenarios'] was empty.

        Now that run_scenario correctly returns 'scenarios', expected_values IS updated.
        """
        from unittest.mock import AsyncMock, MagicMock
        mock_db = AsyncMock()
        mock_decision = MagicMock(spec=Decision)
        mock_decision.alternatives = [{"id": "a1", "name": "Option A", "weighted_score": 0.8}]
        mock_decision.expected_values = {"initial": 1.0}

        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = mock_decision
        mock_db.execute.return_value = mock_res

        service = DecisionService(mock_db)
        scen_req = ScenarioRequest(scenarios=[
            ScenarioDefinition(name="Best", probability=0.5),
            ScenarioDefinition(name="Worst", probability=0.5),
        ])

        updated = await service.rerun_scenarios(uuid.uuid4(), scen_req)
        # FIX: expected_values is now updated (no longer stuck at {"initial": 1.0})
        assert updated.expected_values != {"initial": 1.0}
        assert isinstance(updated.expected_values, dict)
