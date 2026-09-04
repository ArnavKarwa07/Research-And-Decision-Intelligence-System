"""Deterministic calculation engine for decision intelligence.

Provides pure-Python functions for:
- Multi-criteria decision analysis (weighted scoring matrices)
- Best / Base / Worst scenario simulations
- Criteria weight sensitivity stress-testing (tipping point analysis)
- Probabilistic expected value calculations
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Optional


def _is_invalid_number(val: Any) -> bool:
    """Helper to check if a value is not a valid finite non-boolean number."""
    if isinstance(val, bool) or val is None:
        return True
    try:
        f = float(val)
        return math.isnan(f) or math.isinf(f)
    except (ValueError, TypeError):
        return True


def compare_options(
    alternatives: List[Dict[str, Any]],
    criteria: List[Dict[str, Any]],
    clamp_scores: bool = True,
    equal_weights_on_zero: bool = True,
) -> Dict[str, Any]:
    """Calculate normalized multi-criteria decision matrix and rank alternatives.

    Normalizes criteria weights so they sum to 1.0. Computes weighted score per
    alternative: S_i = sum_j (w_j * s_ij). Validates that scores s_ij in [0.0, 1.0].
    Sorts alternatives descending by weighted_score.

    Args:
        alternatives: List of alternative dicts, each with 'id', 'name', and 'scores' dict.
        criteria: List of criterion dicts, each with 'id', 'name', and 'weight' (float).
        clamp_scores: If True, clamp out-of-bounds scores to [0.0, 1.0]; if False, raise ValueError.
        equal_weights_on_zero: If True, assign equal weights when weights sum to 0; if False, raise ValueError.

    Returns:
        Dict containing ranked_alternatives, criteria, weighted_matrix, recommendation, and confidence.
    """
    if not alternatives:
        raise ValueError("Alternatives list cannot be empty.")
    if not criteria:
        raise ValueError("Criteria list cannot be empty.")

    # Validate criteria weights
    raw_weights: List[float] = []
    for c in criteria:
        w_val = c.get("weight", 0.0)
        if _is_invalid_number(w_val):
            raise ValueError("invalid numeric weight")
        w = float(w_val)
        if w < 0.0:
            raise ValueError("negative weight")
        raw_weights.append(w)

    # 1. Normalize criteria weights
    total_weight = sum(raw_weights)
    num_criteria = len(criteria)

    if math.isclose(total_weight, 0.0, abs_tol=1e-9):
        if equal_weights_on_zero:
            norm_weights = [1.0 / num_criteria for _ in range(num_criteria)]
        else:
            raise ValueError("Sum of criteria weights must be greater than zero.")
    else:
        norm_weights = [w / total_weight for w in raw_weights]

    normalized_criteria: List[Dict[str, Any]] = []
    for c, norm_w, raw_w in zip(criteria, norm_weights, raw_weights):
        cid = str(c.get("id", c.get("name", "")))
        cname = str(c.get("name", cid))
        normalized_criteria.append({
            "id": cid,
            "name": cname,
            "weight": round(norm_w, 6),
            "raw_weight": raw_w,
            "description": c.get("description", ""),
        })

    # 2. Score alternatives and build weighted matrix
    scored_alternatives: List[Dict[str, Any]] = []
    matrix: Dict[str, Dict[str, float]] = {}

    for alt in alternatives:
        alt_id = str(alt.get("id", alt.get("name", "")))
        alt_name = str(alt.get("name", alt_id))
        if not alt_id and not alt_name:
            raise ValueError("Each alternative must have an 'id' or 'name'.")

        scores_dict = alt.get("scores") if isinstance(alt.get("scores"), dict) else {}

        weighted_score_exact = 0.0
        alt_matrix_row: Dict[str, float] = {}
        extracted_scores: Dict[str, float] = {}

        for c, norm_w in zip(normalized_criteria, norm_weights):
            cid = c["id"]
            cname = c["name"]

            # Locate score from scores_dict or alt root
            raw_score = None
            if cid in scores_dict:
                raw_score = scores_dict[cid]
            elif cname in scores_dict:
                raw_score = scores_dict[cname]
            elif cid.lower() in scores_dict:
                raw_score = scores_dict[cid.lower()]
            elif cname.lower() in scores_dict:
                raw_score = scores_dict[cname.lower()]
            elif cid in alt:
                raw_score = alt[cid]
            elif cname in alt:
                raw_score = alt[cname]

            if raw_score is None:
                raise ValueError("missing score")

            if _is_invalid_number(raw_score):
                raise ValueError("invalid numeric score")

            val = float(raw_score)

            if -1e-7 <= val < 0.0:
                clamped_score = 0.0
            elif 1.0 < val <= 1.0 + 1e-7:
                clamped_score = 1.0
            elif val < 0.0 or val > 1.0:
                if clamp_scores:
                    clamped_score = max(0.0, min(1.0, val))
                else:
                    raise ValueError("out of bounds score")
            else:
                clamped_score = val

            weighted_contrib = clamped_score * norm_w
            weighted_score_exact += weighted_contrib
            alt_matrix_row[cid] = round(weighted_contrib, 4)
            extracted_scores[cid] = clamped_score

        matrix[alt_id] = alt_matrix_row
        if alt_name != alt_id:
            matrix[alt_name] = alt_matrix_row

        scored_alt = copy.deepcopy(alt)
        scored_alt["id"] = alt_id
        scored_alt["name"] = alt_name
        scored_alt["_exact_weighted_score"] = weighted_score_exact
        scored_alt["weighted_score"] = round(weighted_score_exact, 4)
        scored_alt["scores"] = extracted_scores
        scored_alternatives.append(scored_alt)

    # 3. Sort alternatives descending by exact weighted score, with deterministic tie-breaking (ascending name)
    scored_alternatives.sort(key=lambda x: (-x["_exact_weighted_score"], x["name"]))

    for rank_idx, alt_entry in enumerate(scored_alternatives, start=1):
        alt_entry.pop("_exact_weighted_score", None)
        alt_entry["rank"] = rank_idx

    recommendation = scored_alternatives[0]["name"] if scored_alternatives else ""

    # Calculate confidence based on margin of victory between top 1 and top 2
    if len(scored_alternatives) >= 2:
        margin = scored_alternatives[0]["weighted_score"] - scored_alternatives[1]["weighted_score"]
        confidence = round(max(0.0, margin), 4)
    else:
        confidence = 1.0

    return {
        "ranked_alternatives": scored_alternatives,
        "criteria": normalized_criteria,
        "weighted_matrix": matrix,
        "recommendation": recommendation,
        "confidence": confidence,
    }


def run_scenario(
    alternatives: List[Dict[str, Any]],
    scenarios: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Evaluate alternatives across probabilistic scenarios.

    Validates scenario probabilities sum to 1.0 (within 1e-4 tolerance).
    Evaluates each alternative across best/base/worst or custom scenarios.
    Computes scenario-weighted payoff per alternative: P_i = sum_k (prob_k * val_ik).

    Args:
        alternatives: List of alternatives.
        scenarios: List of scenario dicts, each with 'name', 'probability', and optional payoffs/outcomes.

    Returns:
        Dict containing scenarios, scenario_results, expected_payoffs, and top_scenario_pick.
    """
    if not scenarios:
        raise ValueError("Scenarios list cannot be empty.")
    if not alternatives:
        raise ValueError("Alternatives list cannot be empty.")

    # 1. Validate & Normalize scenario probabilities
    probs: List[float] = []
    tot_prob = 0.0

    for s in scenarios:
        p_val = s.get("probability", s.get("prob", s.get("p", 0.0)))
        if _is_invalid_number(p_val):
            raise ValueError("invalid numeric probability")
        p = float(p_val)
        if p < 0.0 or p > 1.0:
            raise ValueError("probability outside [0, 1]")
        probs.append(p)
        tot_prob += p

    if tot_prob <= 0:
        raise ValueError("Total probability across scenarios must be greater than zero.")

    if not math.isclose(tot_prob, 1.0, abs_tol=1e-4):
        raise ValueError("probabilities must sum to 1.0")

    normalized_scenarios: List[Dict[str, Any]] = []
    for s, p in zip(scenarios, probs):
        sc_name = str(s.get("name", s.get("id", "")))
        normalized_scenarios.append({
            "id": str(s.get("id", sc_name)),
            "name": sc_name,
            "probability": round(p / tot_prob, 4),
            "description": s.get("description", ""),
            "outcomes": {},
        })

    expected_payoffs: Dict[str, float] = {}
    scenario_details: List[Dict[str, Any]] = []
    by_scenario: Dict[str, Dict[str, Any]] = {
        sc["name"]: {
            "probability": sc["probability"],
            "payoffs": {},
            "top_alternative": "",
        }
        for sc in normalized_scenarios
    }

    for alt in alternatives:
        alt_id = str(alt.get("id", alt.get("name", "")))
        alt_name = str(alt.get("name", alt_id))
        outcomes = alt.get("scenario_outcomes", alt.get("scenarios", alt.get("payoffs", {})))
        base_score = float(alt.get("weighted_score", alt.get("score", 0.5)))

        alt_payoff = 0.0
        alt_scenario_breakdown: Dict[str, Dict[str, float]] = {}

        for orig_s, sc in zip(scenarios, normalized_scenarios):
            sc_name = sc["name"]
            prob = sc["probability"]

            # Locate payoff value
            val = None

            # 1. From scenario dict containers
            for container_name in ("payoffs", "values", "outcomes", "scenario_outcomes"):
                container = orig_s.get(container_name)
                if isinstance(container, dict):
                    if alt_name in container:
                        val = container[alt_name]
                    elif alt_id in container:
                        val = container[alt_id]
                if val is not None:
                    break

            # 2. Direct key in scenario
            if val is None:
                if alt_name in orig_s and alt_name not in ("name", "id", "probability", "prob", "p", "description"):
                    val = orig_s[alt_name]
                elif alt_id in orig_s and alt_id not in ("name", "id", "probability", "prob", "p", "description"):
                    val = orig_s[alt_id]

            # 3. From alternative dict containers
            if val is None and isinstance(outcomes, dict):
                if sc_name in outcomes:
                    val = outcomes[sc_name]
                elif sc["id"] in outcomes:
                    val = outcomes[sc["id"]]
                elif sc_name.lower() in outcomes:
                    val = outcomes[sc_name.lower()]

            # 4. Fallback heuristic for standard named scenarios
            if val is None:
                if "best" in sc_name.lower() or "optimistic" in sc_name.lower():
                    val = min(1.0, base_score * 1.25)
                elif "worst" in sc_name.lower() or "pessimistic" in sc_name.lower():
                    val = max(0.0, base_score * 0.65)
                else:
                    val = base_score

            if _is_invalid_number(val):
                raise ValueError("invalid numeric payoff")

            val_float = float(val)
            contrib = val_float * prob
            alt_payoff += contrib

            alt_scenario_breakdown[sc_name] = {
                "projected_value": round(val_float, 4),
                "weighted_contribution": round(contrib, 4),
            }
            sc["outcomes"][alt_name] = round(val_float, 4)
            by_scenario[sc_name]["payoffs"][alt_name] = round(val_float, 4)

        expected_payoffs[alt_name] = round(alt_payoff, 4)
        scenario_details.append({
            "alternative_id": alt_id,
            "alternative_name": alt_name,
            "expected_payoff": round(alt_payoff, 4),
            "scenarios": alt_scenario_breakdown,
        })

    # Determine top pick
    scenario_details.sort(
        key=lambda x: (x["expected_payoff"], -ord(x["alternative_name"][0]) if x["alternative_name"] else 0),
        reverse=True,
    )
    top_pick = scenario_details[0]["alternative_name"] if scenario_details else ""

    return {
        "scenarios": normalized_scenarios,
        "scenario_results": scenario_details,
        "expected_payoffs": expected_payoffs,
        "top_scenario_pick": top_pick,
    }


def run_sensitivity(
    alternatives: List[Dict[str, Any]],
    criteria: List[Dict[str, Any]],
    step_size: float = 0.01,
) -> Dict[str, Any]:
    """Execute criteria weight sensitivity stress-testing to find recommendation tipping points.

    Iterates each criterion's weight from 0.0 to 1.0 in step_size increments,
    re-normalizing other criteria proportionally.
    Detects crossover/switch points where the top-ranked alternative changes from
    the baseline recommendation.

    Args:
        alternatives: List of alternative dicts with scores per criterion.
        criteria: List of criterion dicts with weights.
        step_size: Step size for weight perturbation (default 0.01).

    Returns:
        Dict containing baseline_recommendation, switch_points, and total_criteria_tested.
    """
    if _is_invalid_number(step_size) or step_size <= 0.0 or step_size > 0.5:
        raise ValueError("step_size must be strictly between 0.0 and 0.5.")

    baseline_result = compare_options(alternatives, criteria)
    baseline_rec = baseline_result["recommendation"]
    norm_criteria = baseline_result["criteria"]
    num_criteria = len(norm_criteria)

    if num_criteria <= 1 or len(alternatives) <= 1:
        return {
            "baseline_recommendation": baseline_rec,
            "switch_points": [],
            "total_criteria_tested": num_criteria,
            "notes": "Sensitivity analysis requires 2 or more criteria and alternatives.",
        }

    switch_points: List[Dict[str, Any]] = []

    for idx, c in enumerate(norm_criteria):
        cid = str(c.get("id", c.get("name", "")))
        cname = str(c.get("name", cid))
        orig_weight = float(c.get("weight", 1.0 / num_criteria))

        other_orig_sum = sum(
            float(norm_criteria[j].get("weight", 0)) for j in range(num_criteria) if j != idx
        )

        def _evaluate_at_weight(w_test: float) -> str:
            w_test = max(0.0, min(1.0, w_test))
            rem_weight = max(0.0, 1.0 - w_test)
            perturbed_criteria = []
            for j in range(num_criteria):
                base_c = norm_criteria[j]
                if j == idx:
                    perturbed_criteria.append({**base_c, "weight": w_test})
                else:
                    if other_orig_sum > 1e-9:
                        prop_w = (float(base_c.get("weight", 0)) / other_orig_sum) * rem_weight
                    else:
                        prop_w = rem_weight / (num_criteria - 1)
                    perturbed_criteria.append({**base_c, "weight": prop_w})

            res = compare_options(alternatives, perturbed_criteria, clamp_scores=True)
            return res["recommendation"]

        # Search for tipping point when varying weight away from orig_weight
        # 1. Search downwards from orig_weight to 0.0
        switched = False
        threshold_w = orig_weight
        switches_to = ""

        # Step count downwards
        w_curr = orig_weight
        while w_curr >= 0.0:
            rec = _evaluate_at_weight(w_curr)
            if rec != baseline_rec:
                switched = True
                switches_to = rec
                # Threshold is the boundary where it switched
                threshold_w = w_curr
                break
            w_curr = round(w_curr - step_size, 6)

        # 2. If no downward switch found, search upwards from orig_weight to 1.0
        if not switched:
            w_curr = orig_weight
            while w_curr <= 1.0:
                rec = _evaluate_at_weight(w_curr)
                if rec != baseline_rec:
                    switched = True
                    switches_to = rec
                    threshold_w = w_curr
                    break
                w_curr = round(w_curr + step_size, 6)

        if switched:
            # Frame the switch as "crossing the threshold weight upward changes FROM X TO Y".
            # Downward search: we found that at threshold_w < orig_weight the recommendation
            #   changed to `switches_to` (some other alt).  That means:
            #     - Below the threshold → switches_to wins
            #     - Above the threshold → baseline_rec wins
            #   => switches_from = switches_to (winner below threshold)
            #      switches_to   = baseline_rec (winner above threshold)
            # Upward search: baseline won until threshold_w, then `switches_to` took over:
            #   => switches_from = baseline_rec
            #      switches_to   = the winner above threshold
            if threshold_w < orig_weight:
                final_switches_from = switches_to   # alt that wins when weight is LOW
                final_switches_to = baseline_rec    # baseline wins when weight is HIGH
            else:
                final_switches_from = baseline_rec  # baseline wins when weight is LOW
                final_switches_to = switches_to     # other alt wins when weight is HIGH
            switch_points.append({
                "criterion_id": cid,
                "criterion_name": cname,
                "original_weight": round(orig_weight, 4),
                "threshold_weight": round(threshold_w, 4),
                "switches_from": final_switches_from,
                "switches_to": final_switches_to,
                "sensitivity_level": "high" if abs(threshold_w - orig_weight) < 0.15 else "medium",
            })

    return {
        "baseline_recommendation": baseline_rec,
        "switch_points": switch_points,
        "total_criteria_tested": num_criteria,
    }


def calculate_expected_value(scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate expected value EV = sum(prob_k * value_k) across probabilistic scenarios.

    Validates that scenario probability distribution sums to 1.0 (within 1e-4 tolerance).

    Args:
        scenarios: List of scenario dicts, each with 'probability' and 'outcomes'/'values'/'payoffs'.

    Returns:
        Dict containing expected_values per alternative and best_ev_alternative.
    """
    if not scenarios:
        raise ValueError("Scenarios list cannot be empty.")

    tot_prob = 0.0
    for s in scenarios:
        p_val = s.get("probability", s.get("prob", s.get("p", 0.0)))
        if _is_invalid_number(p_val):
            raise ValueError("invalid numeric probability")
        p = float(p_val)
        if p < 0.0 or p > 1.0:
            raise ValueError("probability outside [0, 1]")
        tot_prob += p

    if tot_prob <= 0:
        raise ValueError("Total probability across scenarios must be positive.")

    if not math.isclose(tot_prob, 1.0, abs_tol=1e-4):
        raise ValueError("probabilities must sum to 1.0")

    ev_totals: Dict[str, float] = {}

    # Extract all outcomes per scenario
    scenario_outcomes_list: List[Dict[str, float]] = []
    all_alts: set[str] = set()

    for s in scenarios:
        prob = float(s.get("probability", s.get("prob", s.get("p", 0.0)))) / tot_prob

        outcomes = s.get("outcomes") or s.get("values") or s.get("payoffs") or s.get("scenario_outcomes")
        if outcomes is None:
            # Check flat keys
            reserved = {"name", "id", "probability", "prob", "p", "description", "metadata", "notes"}
            outcomes = {k: v for k, v in s.items() if k not in reserved and not isinstance(v, (dict, list))}

        extracted: Dict[str, float] = {}
        for alt_name, raw_val in outcomes.items():
            if _is_invalid_number(raw_val):
                raise ValueError("invalid numeric payoff")
            extracted[alt_name] = float(raw_val)
            all_alts.add(alt_name)

        scenario_outcomes_list.append(extracted)

    if not all_alts:
        raise ValueError("No alternative outcomes found across scenarios.")

    for alt_name in sorted(all_alts):
        ev = 0.0
        for s, outcomes in zip(scenarios, scenario_outcomes_list):
            sc_name = s.get("name", s.get("id", "scenario"))
            if alt_name not in outcomes:
                raise ValueError("missing payoff")
            prob = float(s.get("probability", s.get("prob", s.get("p", 0.0)))) / tot_prob
            ev += outcomes[alt_name] * prob
        ev_totals[alt_name] = round(ev, 4)

    best_alt = max(ev_totals.items(), key=lambda x: (x[1], -ord(x[0][0]) if x[0] else 0))[0] if ev_totals else ""

    return {
        "expected_values": ev_totals,
        "best_ev_alternative": best_alt,
    }
