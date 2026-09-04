"""Materiality Scoring Engine service for Phase 12 Continuous Intelligence."""
import logging
import math
from typing import Dict, Any, Union

from app.models.monitoring import MaterialityLevel
from app.schemas.monitoring import MaterialityScoreBreakdown

logger = logging.getLogger(__name__)


def _sanitize_score(val: Any) -> float:
    """Safely convert val to float in [0.0, 1.0], guarding against NaN and Inf."""
    if val is None:
        return 0.0
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return max(0.0, min(1.0, f))
    except (ValueError, TypeError):
        return 0.0


class MaterialityScoringEngine:
    """
    Mathematical scoring engine calculating composite materiality score M in [0.0, 1.0]:
    M = 0.35 * S_assumption + 0.25 * S_contradiction + 0.25 * S_matrix + 0.15 * S_source
    """

    WEIGHT_ASSUMPTION: float = 0.35
    WEIGHT_CONTRADICTION: float = 0.25
    WEIGHT_MATRIX: float = 0.25
    WEIGHT_SOURCE: float = 0.15

    @staticmethod
    def classify_materiality_level(score: float) -> MaterialityLevel:
        """
        Classify numerical materiality score into MaterialityLevel enum.

        Boundaries:
        - NEGLIGIBLE (< 0.2)
        - LOW (< 0.4)
        - MEDIUM (< 0.6)
        - HIGH (< 0.8)
        - CRITICAL (>= 0.8)
        """
        if score is None:
            return MaterialityLevel.NEGLIGIBLE
        try:
            val = float(score)
            if math.isnan(val) or math.isinf(val):
                return MaterialityLevel.NEGLIGIBLE
        except (ValueError, TypeError):
            return MaterialityLevel.NEGLIGIBLE

        s = max(0.0, min(1.0, val))
        if s < 0.2:
            return MaterialityLevel.NEGLIGIBLE
        elif s < 0.4:
            return MaterialityLevel.LOW
        elif s < 0.6:
            return MaterialityLevel.MEDIUM
        elif s < 0.8:
            return MaterialityLevel.HIGH
        else:
            return MaterialityLevel.CRITICAL

    @classmethod
    def calculate_materiality_score(
        cls,
        s_assumption: float,
        s_contradiction: float,
        s_matrix: float,
        s_source: float,
    ) -> MaterialityScoreBreakdown:
        """
        Calculate composite materiality score M and return detailed factor breakdown.

        Args:
            s_assumption: Sub-score for assumption invalidations in [0.0, 1.0]
            s_contradiction: Sub-score for claim additions/contradictions in [0.0, 1.0]
            s_matrix: Sub-score for decision option score drifts / recommendation flips in [0.0, 1.0]
            s_source: Sub-score for source reliability changes in [0.0, 1.0]

        Returns:
            MaterialityScoreBreakdown Pydantic schema with factor breakdown and materiality level.
        """
        s_ass = _sanitize_score(s_assumption)
        s_con = _sanitize_score(s_contradiction)
        s_mat = _sanitize_score(s_matrix)
        s_src = _sanitize_score(s_source)

        raw_total = (
            cls.WEIGHT_ASSUMPTION * s_ass
            + cls.WEIGHT_CONTRADICTION * s_con
            + cls.WEIGHT_MATRIX * s_mat
            + cls.WEIGHT_SOURCE * s_src
        )

        total_score = round(max(0.0, min(1.0, raw_total)), 4)
        level = cls.classify_materiality_level(total_score)

        return MaterialityScoreBreakdown(
            claims_delta_score=s_con,
            sources_delta_score=s_src,
            assumptions_delta_score=s_ass,
            recommendation_flip_score=s_mat,
            total_score=total_score,
            materiality_level=level.value,
        )

    @classmethod
    def score_delta_result(cls, delta_result: Dict[str, Any]) -> MaterialityScoreBreakdown:
        """
        Extract sub-scores from a BaselineDeltaResult dictionary and calculate score breakdown.
        """
        sub_scores = delta_result.get("sub_scores") or {}
        s_assumption = _sanitize_score(sub_scores.get("s_assumption"))
        s_contradiction = _sanitize_score(sub_scores.get("s_contradiction"))
        s_matrix = _sanitize_score(sub_scores.get("s_matrix"))
        s_source = _sanitize_score(sub_scores.get("s_source"))

        return cls.calculate_materiality_score(
            s_assumption=s_assumption,
            s_contradiction=s_contradiction,
            s_matrix=s_matrix,
            s_source=s_source,
        )
