"""Evaluation Metrics Engine.

Computes exact mathematical metrics for:
1. Vector / RAG Retrieval: Precision@K, Recall@K, MRR, NDCG.
2. Claim Verification: Hallucination Rate, Faithfulness, Evidence Groundedness.
3. Citation & Trajectory: Citation Coverage/Precision, Trajectory Efficiency, Tool Accuracy, Re-plan Penalty.
4. Decision Quality: MCDA Criteria Weight Alignment, Scenario Payoff Alignment, Sensitivity Validity.
"""
import math
from typing import Any, Sequence
import logging

from app.schemas.eval import (
    RetrievalMetrics,
    ClaimVerificationMetrics,
    CitationMetrics,
    TrajectoryMetrics,
    DecisionQualityMetrics,
)

logger = logging.getLogger(__name__)


def compute_retrieval_metrics(
    retrieved_chunk_ids: list[str],
    ground_truth_chunk_ids: list[str],
    k: int = 5,
) -> RetrievalMetrics:
    """
    Compute Precision@K, Recall@K, MRR, and NDCG for retrieved context chunks.
    """
    if not retrieved_chunk_ids or not ground_truth_chunk_ids:
        return RetrievalMetrics(precision_at_k=0.0, recall_at_k=0.0, mrr=0.0, ndcg=0.0)

    top_k = retrieved_chunk_ids[:k]
    gt_set = set(ground_truth_chunk_ids)

    # Precision@K & Recall@K
    relevant_in_top_k = sum(1 for cid in top_k if cid in gt_set)
    precision_at_k = round(relevant_in_top_k / float(k), 4)
    recall_at_k = round(relevant_in_top_k / float(len(gt_set)), 4)

    # MRR (Mean Reciprocal Rank)
    mrr = 0.0
    for idx, cid in enumerate(retrieved_chunk_ids, start=1):
        if cid in gt_set:
            mrr = round(1.0 / idx, 4)
            break

    # NDCG@K
    dcg = 0.0
    for idx, cid in enumerate(top_k, start=1):
        rel = 1.0 if cid in gt_set else 0.0
        dcg += rel / math.log2(idx + 1)

    idcg = 0.0
    for idx in range(1, min(len(gt_set), k) + 1):
        idcg += 1.0 / math.log2(idx + 1)

    ndcg = round(dcg / idcg, 4) if idcg > 0 else 0.0

    return RetrievalMetrics(
        precision_at_k=precision_at_k,
        recall_at_k=recall_at_k,
        mrr=mrr,
        ndcg=ndcg,
    )


def compute_claim_verification_metrics(
    generated_claims: list[dict[str, Any]],
    ground_truth_claims: list[dict[str, Any]],
) -> ClaimVerificationMetrics:
    """
    Compute Hallucination Rate, Faithfulness Score, and Evidence Groundedness.
    """
    if not generated_claims:
        return ClaimVerificationMetrics(
            hallucination_rate=0.0, faithfulness_score=1.0, evidence_groundedness_score=1.0
        )

    total_claims = len(generated_claims)
    grounded_count = 0
    faithfulness_scores: list[float] = []

    gt_claim_texts = [str(c.get("text", c.get("claim_text", ""))).lower().strip() for c in ground_truth_claims]

    for claim in generated_claims:
        text = str(claim.get("text", claim.get("claim_text", ""))).lower().strip()
        is_supported = claim.get("is_supported", claim.get("verification_status") == "verified")
        confidence = float(claim.get("confidence", 0.8))

        if is_supported or any(gt in text or text in gt for gt in gt_claim_texts if gt):
            grounded_count += 1
            faithfulness_scores.append(confidence)
        else:
            faithfulness_scores.append(max(0.0, confidence - 0.5))

    evidence_groundedness = round(grounded_count / float(total_claims), 4)
    hallucination_rate = round(1.0 - evidence_groundedness, 4)
    avg_faithfulness = round(sum(faithfulness_scores) / float(len(faithfulness_scores)), 4) if faithfulness_scores else 0.0

    return ClaimVerificationMetrics(
        hallucination_rate=hallucination_rate,
        faithfulness_score=avg_faithfulness,
        evidence_groundedness_score=evidence_groundedness,
    )


def compute_citation_metrics(
    claims_with_citations: list[dict[str, Any]],
) -> CitationMetrics:
    """
    Compute Citation Coverage and Citation Precision.
    """
    if not claims_with_citations:
        return CitationMetrics(citation_coverage=0.0, citation_precision=0.0)

    total_claims = len(claims_with_citations)
    cited_claims = 0
    valid_citations = 0
    total_citations = 0

    for claim in claims_with_citations:
        citations = claim.get("citations", claim.get("sources", []))
        if citations:
            cited_claims += 1
            total_citations += len(citations)
            valid_citations += sum(1 for c in citations if c.get("is_valid", True))

    coverage = round(cited_claims / float(total_claims), 4)
    precision = round(valid_citations / float(total_citations), 4) if total_citations > 0 else 0.0

    return CitationMetrics(
        citation_coverage=coverage,
        citation_precision=precision,
    )


def compute_trajectory_metrics(
    actual_steps: list[dict[str, Any]],
    expected_optimal_step_count: int = 5,
    replan_count: int = 0,
    useless_replans: int = 0,
) -> TrajectoryMetrics:
    """
    Compute Trajectory Efficiency, Tool Call Accuracy, and Unnecessary Re-plan Penalty.
    """
    actual_count = len(actual_steps) if actual_steps else 1
    efficiency = round(min(1.0, float(expected_optimal_step_count) / float(actual_count)), 4)

    tool_calls = [step for step in actual_steps if step.get("tool_name")]
    if tool_calls:
        correct_tools = sum(1 for step in tool_calls if step.get("status") == "success" and not step.get("error"))
        tool_accuracy = round(correct_tools / float(len(tool_calls)), 4)
    else:
        tool_accuracy = 1.0

    replan_penalty = 0.0
    if replan_count > 0:
        penalty_ratio = useless_replans / float(replan_count)
        replan_penalty = round(min(1.0, penalty_ratio * 0.5 + (useless_replans * 0.1)), 4)

    return TrajectoryMetrics(
        trajectory_efficiency=efficiency,
        tool_call_accuracy=tool_accuracy,
        unnecessary_replan_penalty=replan_penalty,
    )


def compute_decision_quality_metrics(
    actual_decision_matrix: dict[str, Any],
    expected_decision_matrix: dict[str, Any],
    actual_rankings: list[str],
    expected_rankings: list[str],
) -> DecisionQualityMetrics:
    """
    Compute MCDA Criteria Weight Alignment, Scenario Payoff Alignment, and Sensitivity Validity.
    """
    # 1. Criteria Weighting Alignment
    actual_criteria = actual_decision_matrix.get("criteria", [])
    expected_criteria = expected_decision_matrix.get("criteria", [])

    if actual_criteria and expected_criteria:
        actual_weights = {c.get("name"): float(c.get("weight", 0.0)) for c in actual_criteria}
        expected_weights = {c.get("name"): float(c.get("weight", 0.0)) for c in expected_criteria}

        shared_keys = set(actual_weights.keys()).intersection(set(expected_weights.keys()))
        if shared_keys:
            errors = [abs(actual_weights[k] - expected_weights[k]) for k in shared_keys]
            mae = sum(errors) / float(len(errors))
            weight_score = round(max(0.0, 1.0 - mae), 4)
        else:
            weight_score = 0.5
    else:
        weight_score = 0.8

    # 2. Scenario Payoff / Ranking Alignment
    if actual_rankings and expected_rankings:
        top_actual = actual_rankings[0] if actual_rankings else None
        top_expected = expected_rankings[0] if expected_rankings else None
        if top_actual == top_expected:
            payoff_score = 1.0
        elif top_actual in expected_rankings[:2]:
            payoff_score = 0.75
        else:
            payoff_score = 0.33
    else:
        payoff_score = 0.85

    # 3. Sensitivity Tipping Point Validity
    tipping_points = actual_decision_matrix.get("sensitivity_points", actual_decision_matrix.get("switch_points", []))
    valid_points = sum(1 for tp in tipping_points if 0.0 <= float(tp.get("threshold", tp.get("switch_weight", 0.5))) <= 1.0)
    sensitivity_score = round(valid_points / float(len(tipping_points)), 4) if tipping_points else 0.9

    return DecisionQualityMetrics(
        mcda_criteria_weighting_score=weight_score,
        scenario_payoff_alignment=payoff_score,
        sensitivity_tipping_point_validity=sensitivity_score,
    )
