"""Unit tests for deterministic decision tools module."""

import math
import pytest

from app.tools.decision_tools import (
    compare_options,
    run_scenario,
    run_sensitivity,
    calculate_expected_value,
)


class TestCompareOptions:
    """Tests for compare_options function."""

    def test_basic_comparison(self):
        alternatives = [
            {"id": "a1", "name": "Option A", "scores": {"c1": 0.9, "c2": 0.4}},
            {"id": "a2", "name": "Option B", "scores": {"c1": 0.3, "c2": 0.8}},
        ]
        criteria = [
            {"id": "c1", "name": "Criterion 1", "weight": 0.6},
            {"id": "c2", "name": "Criterion 2", "weight": 0.4},
        ]

        result = compare_options(alternatives, criteria)

        # A: 0.6 * 0.9 + 0.4 * 0.4 = 0.54 + 0.16 = 0.70
        # B: 0.6 * 0.3 + 0.4 * 0.8 = 0.18 + 0.32 = 0.50
        assert result["recommendation"] == "Option A"
        assert math.isclose(result["confidence"], 0.20, abs_tol=1e-4)

        ranked = result["ranked_alternatives"]
        assert len(ranked) == 2
        assert ranked[0]["name"] == "Option A"
        assert ranked[0]["rank"] == 1
        assert math.isclose(ranked[0]["weighted_score"], 0.70, abs_tol=1e-4)
        assert ranked[1]["name"] == "Option B"
        assert ranked[1]["rank"] == 2
        assert math.isclose(ranked[1]["weighted_score"], 0.50, abs_tol=1e-4)

        # Check weighted matrix
        matrix = result["weighted_matrix"]
        assert "Option A" in matrix
        assert math.isclose(matrix["Option A"]["c1"], 0.54, abs_tol=1e-4)
        assert math.isclose(matrix["Option A"]["c2"], 0.16, abs_tol=1e-4)

    def test_weight_normalization(self):
        alternatives = [
            {"name": "A", "scores": {"c1": 1.0, "c2": 0.0}},
            {"name": "B", "scores": {"c1": 0.0, "c2": 1.0}},
        ]
        # Raw weights sum to 10
        criteria = [
            {"id": "c1", "name": "C1", "weight": 7.0},
            {"id": "c2", "name": "C2", "weight": 3.0},
        ]
        result = compare_options(alternatives, criteria)
        assert math.isclose(result["criteria"][0]["weight"], 0.7, abs_tol=1e-4)
        assert math.isclose(result["criteria"][1]["weight"], 0.3, abs_tol=1e-4)
        assert result["recommendation"] == "A"
        assert math.isclose(result["ranked_alternatives"][0]["weighted_score"], 0.7, abs_tol=1e-4)

    def test_zero_weight_sum(self):
        alternatives = [{"name": "A", "scores": {"c1": 0.5}}]
        criteria = [{"id": "c1", "name": "C1", "weight": 0.0}]

        # By default, zero weight sum raises ValueError
        with pytest.raises(ValueError, match="Sum of criteria weights"):
            compare_options(alternatives, criteria, equal_weights_on_zero=False)

        # With equal_weights_on_zero=True, fallback to equal weights
        res = compare_options(alternatives, criteria, equal_weights_on_zero=True)
        assert math.isclose(res["criteria"][0]["weight"], 1.0, abs_tol=1e-4)

    def test_negative_weight_raises_error(self):
        alternatives = [{"name": "A", "scores": {"c1": 0.5}}]
        criteria = [{"id": "c1", "name": "C1", "weight": -0.5}]
        with pytest.raises(ValueError, match="negative weight"):
            compare_options(alternatives, criteria)

    def test_nan_inf_weight_raises_error(self):
        alternatives = [{"name": "A", "scores": {"c1": 0.5}}]
        criteria = [{"id": "c1", "name": "C1", "weight": float("nan")}]
        with pytest.raises(ValueError, match="invalid numeric weight"):
            compare_options(alternatives, criteria)

        criteria_inf = [{"id": "c1", "name": "C1", "weight": float("inf")}]
        with pytest.raises(ValueError, match="invalid numeric weight"):
            compare_options(alternatives, criteria_inf)

    def test_score_bounds_and_clamping(self):
        alternatives_out_of_bounds = [
            {"name": "A", "scores": {"c1": 1.5}},
        ]
        criteria = [{"id": "c1", "name": "C1", "weight": 1.0}]

        # Out of bounds raises error when clamp_scores=False
        with pytest.raises(ValueError, match="out of bounds"):
            compare_options(alternatives_out_of_bounds, criteria, clamp_scores=False)

        # Clamps when clamp_scores=True
        res = compare_options(alternatives_out_of_bounds, criteria, clamp_scores=True)
        assert math.isclose(res["ranked_alternatives"][0]["weighted_score"], 1.0, abs_tol=1e-4)

    def test_nan_inf_score_raises_error(self):
        alternatives = [{"name": "A", "scores": {"c1": float("nan")}}]
        criteria = [{"id": "c1", "name": "C1", "weight": 1.0}]
        with pytest.raises(ValueError, match="invalid numeric score"):
            compare_options(alternatives, criteria)

    def test_empty_inputs_raise_error(self):
        with pytest.raises(ValueError, match="Alternatives list cannot be empty"):
            compare_options([], [{"id": "c1", "weight": 1.0}])

        with pytest.raises(ValueError, match="Criteria list cannot be empty"):
            compare_options([{"name": "A", "scores": {}}], [])

    def test_single_alternative(self):
        alternatives = [{"name": "Solo", "scores": {"c1": 0.75}}]
        criteria = [{"id": "c1", "weight": 1.0}]
        result = compare_options(alternatives, criteria)
        assert result["recommendation"] == "Solo"
        assert result["confidence"] == 1.0
        assert len(result["ranked_alternatives"]) == 1
        assert result["ranked_alternatives"][0]["rank"] == 1

    def test_tie_breaking(self):
        alternatives = [
            {"name": "Option Z", "scores": {"c1": 0.8}},
            {"name": "Option A", "scores": {"c1": 0.8}},
        ]
        criteria = [{"id": "c1", "weight": 1.0}]
        result = compare_options(alternatives, criteria)
        # Alphabetical tie-breaking: Option A comes first
        assert result["ranked_alternatives"][0]["name"] == "Option A"
        assert result["confidence"] == 0.0

    def test_missing_score_raises_error(self):
        alternatives = [{"name": "A", "scores": {"c1": 0.8}}]
        criteria = [
            {"id": "c1", "weight": 0.5},
            {"id": "c2", "weight": 0.5},
        ]
        with pytest.raises(ValueError, match="missing score"):
            compare_options(alternatives, criteria)


class TestRunScenario:
    """Tests for run_scenario function."""

    def test_basic_scenario_evaluation(self):
        alternatives = [
            {
                "name": "Alt 1",
                "scenarios": {"worst": 20.0, "base": 50.0, "best": 100.0},
            },
            {
                "name": "Alt 2",
                "scenarios": {"worst": 35.0, "base": 55.0, "best": 70.0},
            },
        ]
        scenarios = [
            {"name": "worst", "probability": 0.2},
            {"name": "base", "probability": 0.6},
            {"name": "best", "probability": 0.2},
        ]

        result = run_scenario(alternatives, scenarios)

        # Alt 1: 0.2*20 + 0.6*50 + 0.2*100 = 4 + 30 + 20 = 54.0
        # Alt 2: 0.2*35 + 0.6*55 + 0.2*70 = 7 + 33 + 14 = 54.0
        assert math.isclose(result["expected_payoffs"]["Alt 1"], 54.0, abs_tol=1e-4)
        assert math.isclose(result["expected_payoffs"]["Alt 2"], 54.0, abs_tol=1e-4)
        assert result["top_scenario_pick"] in ("Alt 1", "Alt 2")

    def test_scenario_payoffs_in_scenario_dict(self):
        alternatives = [{"name": "Stock"}, {"name": "Bond"}]
        scenarios = [
            {"name": "Boom", "probability": 0.3, "payoffs": {"Stock": 200.0, "Bond": 50.0}},
            {"name": "Recession", "probability": 0.7, "payoffs": {"Stock": -50.0, "Bond": 60.0}},
        ]
        result = run_scenario(alternatives, scenarios)
        # Stock: 0.3 * 200 + 0.7 * (-50) = 60 - 35 = 25.0
        # Bond:  0.3 * 50  + 0.7 * 60   = 15 + 42 = 57.0
        assert math.isclose(result["expected_payoffs"]["Stock"], 25.0, abs_tol=1e-4)
        assert math.isclose(result["expected_payoffs"]["Bond"], 57.0, abs_tol=1e-4)
        assert result["top_scenario_pick"] == "Bond"

    def test_probability_tolerance_and_invalid_sum(self):
        alternatives = [{"name": "A", "scenarios": {"s1": 10.0, "s2": 20.0}}]

        # Probability sum != 1.0
        invalid_scenarios = [
            {"name": "s1", "probability": 0.4},
            {"name": "s2", "probability": 0.4},
        ]
        with pytest.raises(ValueError, match="probabilities must sum to 1.0"):
            run_scenario(alternatives, invalid_scenarios)

        # Within 1e-4 tolerance
        valid_scenarios = [
            {"name": "s1", "probability": 0.33333},
            {"name": "s2", "probability": 0.66667},
        ]
        res = run_scenario(alternatives, valid_scenarios)
        assert "A" in res["expected_payoffs"]

    def test_negative_or_nan_probability(self):
        alternatives = [{"name": "A", "scenarios": {"s1": 10.0}}]
        with pytest.raises(ValueError, match="outside"):
            run_scenario(alternatives, [{"name": "s1", "probability": -0.1}])
        with pytest.raises(ValueError, match="invalid numeric probability"):
            run_scenario(alternatives, [{"name": "s1", "probability": float("nan")}])

    def test_empty_lists(self):
        with pytest.raises(ValueError, match="Alternatives list cannot be empty"):
            run_scenario([], [{"name": "s", "probability": 1.0}])
        with pytest.raises(ValueError, match="Scenarios list cannot be empty"):
            run_scenario([{"name": "A"}], [])


class TestRunSensitivity:
    """Tests for run_sensitivity function."""

    def test_crossover_switch_point_detected(self):
        # Alt A is strong on C1 (0.9 vs 0.3), Alt B is strong on C2 (0.8 vs 0.2)
        # At baseline: C1 weight = 0.6, C2 weight = 0.4
        # Alt A: 0.6 * 0.9 + 0.4 * 0.2 = 0.62
        # Alt B: 0.6 * 0.3 + 0.4 * 0.8 = 0.50
        # Recommendation: Alt A
        # Crossover occurs when:
        # w1 * 0.9 + (1 - w1) * 0.2 = w1 * 0.3 + (1 - w1) * 0.8
        # 0.2 + 0.7 * w1 = 0.8 - 0.5 * w1 => 1.2 * w1 = 0.6 => w1 = 0.50
        # When w1 < 0.50, Alt B wins; when w1 >= 0.50, Alt A wins.
        alternatives = [
            {"id": "a1", "name": "Alt A", "scores": {"c1": 0.9, "c2": 0.2}},
            {"id": "a2", "name": "Alt B", "scores": {"c1": 0.3, "c2": 0.8}},
        ]
        criteria = [
            {"id": "c1", "name": "Criterion 1", "weight": 0.6},
            {"id": "c2", "name": "Criterion 2", "weight": 0.4},
        ]

        result = run_sensitivity(alternatives, criteria, step_size=0.01)

        assert result["baseline_recommendation"] == "Alt A"
        switch_points = result["switch_points"]
        assert len(switch_points) >= 1

        # Check that crossover occurs near threshold 0.50
        c1_switches = [sp for sp in switch_points if sp["criterion_id"] == "c1"]
        assert len(c1_switches) == 1
        assert math.isclose(c1_switches[0]["threshold_weight"], 0.50, abs_tol=0.02)
        assert c1_switches[0]["switches_from"] == "Alt B"
        assert c1_switches[0]["switches_to"] == "Alt A"

        c2_switches = [sp for sp in switch_points if sp["criterion_id"] == "c2"]
        assert len(c2_switches) == 1
        assert math.isclose(c2_switches[0]["threshold_weight"], 0.50, abs_tol=0.02)
        assert c2_switches[0]["switches_from"] == "Alt A"
        assert c2_switches[0]["switches_to"] == "Alt B"

    def test_single_criterion_returns_empty_switches(self):
        alternatives = [
            {"name": "A", "scores": {"c1": 0.9}},
            {"name": "B", "scores": {"c1": 0.5}},
        ]
        criteria = [{"id": "c1", "weight": 1.0}]
        result = run_sensitivity(alternatives, criteria)
        assert result["baseline_recommendation"] == "A"
        assert result["switch_points"] == []

    def test_single_alternative_returns_empty_switches(self):
        alternatives = [{"name": "Solo", "scores": {"c1": 0.8, "c2": 0.5}}]
        criteria = [
            {"id": "c1", "weight": 0.5},
            {"id": "c2", "weight": 0.5},
        ]
        result = run_sensitivity(alternatives, criteria)
        assert result["baseline_recommendation"] == "Solo"
        assert result["switch_points"] == []

    def test_dominant_alternative_no_crossover(self):
        # Alt A dominates on all criteria
        alternatives = [
            {"name": "A", "scores": {"c1": 0.9, "c2": 0.9}},
            {"name": "B", "scores": {"c1": 0.1, "c2": 0.1}},
        ]
        criteria = [
            {"id": "c1", "weight": 0.5},
            {"id": "c2", "weight": 0.5},
        ]
        result = run_sensitivity(alternatives, criteria)
        assert result["baseline_recommendation"] == "A"
        assert result["switch_points"] == []

    def test_invalid_step_size(self):
        alternatives = [{"name": "A", "scores": {"c1": 0.8}}]
        criteria = [{"id": "c1", "weight": 1.0}]
        with pytest.raises(ValueError, match="step_size"):
            run_sensitivity(alternatives, criteria, step_size=0.0)
        with pytest.raises(ValueError, match="step_size"):
            run_sensitivity(alternatives, criteria, step_size=-0.05)
        with pytest.raises(ValueError, match="step_size"):
            run_sensitivity(alternatives, criteria, step_size=1.5)


class TestCalculateExpectedValue:
    """Tests for calculate_expected_value function."""

    def test_basic_expected_value(self):
        scenarios = [
            {"name": "Bull", "probability": 0.3, "values": {"Tech Fund": 100.0, "Index Fund": 50.0}},
            {"name": "Base", "probability": 0.5, "values": {"Tech Fund": 20.0, "Index Fund": 30.0}},
            {"name": "Bear", "probability": 0.2, "values": {"Tech Fund": -50.0, "Index Fund": 0.0}},
        ]
        result = calculate_expected_value(scenarios)

        # Tech Fund:  0.3*100 + 0.5*20 + 0.2*(-50) = 30 + 10 - 10 = 30.0
        # Index Fund: 0.3*50  + 0.5*30 + 0.2*0     = 15 + 15 + 0  = 30.0
        assert math.isclose(result["expected_values"]["Tech Fund"], 30.0, abs_tol=1e-4)
        assert math.isclose(result["expected_values"]["Index Fund"], 30.0, abs_tol=1e-4)
        assert result["best_ev_alternative"] in ("Index Fund", "Tech Fund")

    def test_flat_keys_in_scenarios(self):
        scenarios = [
            {"name": "High", "probability": 0.4, "Option X": 80.0, "Option Y": 40.0},
            {"name": "Low", "probability": 0.6, "Option X": 10.0, "Option Y": 30.0},
        ]
        result = calculate_expected_value(scenarios)
        # Option X: 0.4*80 + 0.6*10 = 32 + 6 = 38.0
        # Option Y: 0.4*40 + 0.6*30 = 16 + 18 = 34.0
        assert math.isclose(result["expected_values"]["Option X"], 38.0, abs_tol=1e-4)
        assert math.isclose(result["expected_values"]["Option Y"], 34.0, abs_tol=1e-4)
        assert result["best_ev_alternative"] == "Option X"

    def test_probability_validation(self):
        # Probabilities sum != 1.0
        scenarios = [
            {"name": "S1", "probability": 0.5, "values": {"A": 10}},
            {"name": "S2", "probability": 0.2, "values": {"A": 10}},
        ]
        with pytest.raises(ValueError, match="probabilities must sum to 1.0"):
            calculate_expected_value(scenarios)

    def test_missing_alternative_in_scenario(self):
        scenarios = [
            {"name": "S1", "probability": 0.5, "values": {"A": 10, "B": 20}},
            {"name": "S2", "probability": 0.5, "values": {"A": 15}},  # B is missing
        ]
        with pytest.raises(ValueError, match="missing payoff"):
            calculate_expected_value(scenarios)

    def test_nan_or_inf_value_raises_error(self):
        scenarios = [
            {"name": "S1", "probability": 1.0, "values": {"A": float("nan")}},
        ]
        with pytest.raises(ValueError, match="invalid numeric payoff"):
            calculate_expected_value(scenarios)

    def test_empty_scenarios_raises_error(self):
        with pytest.raises(ValueError, match="Scenarios list cannot be empty"):
            calculate_expected_value([])
