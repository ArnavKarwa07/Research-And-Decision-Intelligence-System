"""Unit tests for Evaluation Metrics Engine."""
import pytest
from app.services.eval_metrics_engine import (
    compute_retrieval_metrics,
    compute_claim_verification_metrics,
    compute_citation_metrics,
    compute_trajectory_metrics,
    compute_decision_quality_metrics,
)


def test_compute_retrieval_metrics():
    retrieved = ["chunk_1", "chunk_2", "chunk_3", "chunk_4", "chunk_5"]
    ground_truth = ["chunk_1", "chunk_3"]

    res = compute_retrieval_metrics(retrieved, ground_truth, k=5)
    assert res.precision_at_k == 0.4  # 2 relevant out of 5
    assert res.recall_at_k == 1.0     # 2 relevant out of 2
    assert res.mrr == 1.0             # First relevant at rank 1
    assert res.ndcg > 0.8             # High ranking quality


def test_compute_claim_verification_metrics():
    gen_claims = [
        {"text": "Neon scales to zero", "is_supported": True, "confidence": 0.95},
        {"text": "Earth is flat", "is_supported": False, "confidence": 0.20},
    ]
    gt_claims = [{"text": "Neon scales to zero"}]

    res = compute_claim_verification_metrics(gen_claims, gt_claims)
    assert res.evidence_groundedness_score == 0.5
    assert res.hallucination_rate == 0.5
    assert res.faithfulness_score > 0.0


def test_compute_citation_metrics():
    claims = [
        {"text": "Claim 1", "citations": [{"url": "http://example.com", "is_valid": True}]},
        {"text": "Claim 2", "citations": []},
    ]
    res = compute_citation_metrics(claims)
    assert res.citation_coverage == 0.5
    assert res.citation_precision == 1.0


def test_compute_trajectory_metrics():
    actual_steps = [
        {"step_name": "search", "tool_name": "web_search", "status": "success"},
        {"step_name": "fact_check", "tool_name": "fact_checker", "status": "success"},
    ]
    res = compute_trajectory_metrics(actual_steps, expected_optimal_step_count=2, replan_count=1, useless_replans=0)
    assert res.trajectory_efficiency == 1.0
    assert res.tool_call_accuracy == 1.0
    assert res.unnecessary_replan_penalty == 0.0


def test_compute_decision_quality_metrics():
    actual_matrix = {
        "criteria": [{"name": "Cost", "weight": 0.5}, {"name": "Quality", "weight": 0.5}],
        "sensitivity_points": [{"criterion": "Cost", "threshold": 0.4}],
    }
    expected_matrix = {
        "criteria": [{"name": "Cost", "weight": 0.5}, {"name": "Quality", "weight": 0.5}],
    }
    actual_rankings = ["Option A", "Option B"]
    expected_rankings = ["Option A", "Option B"]

    res = compute_decision_quality_metrics(actual_matrix, expected_matrix, actual_rankings, expected_rankings)
    assert res.mcda_criteria_weighting_score == 1.0
    assert res.scenario_payoff_alignment == 1.0
    assert res.sensitivity_tipping_point_validity == 1.0
