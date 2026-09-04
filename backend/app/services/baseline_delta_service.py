"""Baseline Delta Service for Phase 12 Continuous Intelligence."""
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.monitoring import ResearchBaselineSnapshot
from app.models.query import Query
from app.models.claim import Claim
from app.models.source import Source
from app.models.decision import Decision
from app.schemas.monitoring import BaselineSnapshotCreate

logger = logging.getLogger(__name__)


def _safe_float(val: Any, default: float = 0.0) -> float:
    """Safely convert value to float, returning default if None or invalid."""
    if val is None:
        return default
    try:
        import math
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default


class BaselineDeltaService:
    """
    Manages baseline snapshot creation and computes delta state between baseline snapshots
    and new research run states.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_baseline_snapshot(self, snapshot_in: BaselineSnapshotCreate) -> ResearchBaselineSnapshot:
        """Create and persist a new ResearchBaselineSnapshot."""
        snapshot = ResearchBaselineSnapshot(
            project_id=snapshot_in.project_id,
            session_id=snapshot_in.session_id,
            query_id=snapshot_in.query_id,
            decision_id=snapshot_in.decision_id,
            snapshot_label=snapshot_in.snapshot_label,
            claims_snapshot=snapshot_in.claims_snapshot or [],
            sources_snapshot=snapshot_in.sources_snapshot or [],
            assumptions_snapshot=snapshot_in.assumptions_snapshot or [],
            decision_snapshot=snapshot_in.decision_snapshot or {},
        )
        self.db.add(snapshot)
        await self.db.commit()
        await self.db.refresh(snapshot)
        return snapshot

    async def get_baseline_snapshot(self, snapshot_id: UUID) -> Optional[ResearchBaselineSnapshot]:
        """Retrieve a baseline snapshot by ID."""
        result = await self.db.execute(
            select(ResearchBaselineSnapshot).where(ResearchBaselineSnapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()

    async def create_snapshot_from_query(self, query_id: UUID, snapshot_label: str) -> ResearchBaselineSnapshot:
        """
        Build a baseline snapshot by querying existing Query, Claims, Sources, and Decisions.
        """
        query_res = await self.db.execute(select(Query).where(Query.id == query_id))
        query_obj = query_res.scalar_one_or_none()
        if not query_obj:
            raise ValueError(f"Query with ID '{query_id}' not found.")

        # Claims
        claims_res = await self.db.execute(select(Claim).where(Claim.query_id == query_id))
        claims_list = claims_res.scalars().all()
        claims_snap = [
            {
                "id": str(c.id),
                "content": c.content,
                "claim_type": c.claim_type,
                "confidence": c.confidence,
                "status": c.status,
            }
            for c in claims_list
        ]

        # Sources - Filtered by query_id to prevent query leak
        sources_res = await self.db.execute(select(Source).where(Source.query_id == query_id))
        sources_list = sources_res.scalars().all()
        sources_snap = [
            {
                "id": str(s.id),
                "url": s.url,
                "title": s.title,
                "quality_score": s.quality_score,
                "reliability_rating": s.reliability_rating,
            }
            for s in sources_list
        ]

        # Decisions & Assumptions
        decision_res = await self.db.execute(
            select(Decision).where(Decision.query_id == query_id).order_by(Decision.created_at.desc())
        )
        decision_obj = decision_res.scalars().first()

        decision_snap: Dict[str, Any] = {}
        assumptions_snap: List[Dict[str, Any]] = []

        if decision_obj:
            decision_snap = {
                "id": str(decision_obj.id),
                "recommendation": decision_obj.recommendation,
                "confidence": decision_obj.confidence,
                "alternatives": decision_obj.alternatives or [],
                "criteria": decision_obj.criteria or [],
                "weighted_matrix": decision_obj.weighted_matrix or {},
            }
            assumptions_list = decision_obj.assumptions or []
            assumptions_snap = [
                {"text": str(a) if isinstance(a, str) else a.get("text", ""), "status": "ACTIVE"}
                for a in assumptions_list
            ]

        snapshot_in = BaselineSnapshotCreate(
            project_id=None,
            session_id=query_obj.session_id if hasattr(query_obj, "session_id") else None,
            query_id=query_id,
            decision_id=decision_obj.id if decision_obj else None,
            snapshot_label=snapshot_label,
            claims_snapshot=claims_snap,
            sources_snapshot=sources_snap,
            assumptions_snapshot=assumptions_snap,
            decision_snapshot=decision_snap,
        )
        return await self.create_baseline_snapshot(snapshot_in)

    def compute_delta(
        self, baseline: ResearchBaselineSnapshot, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare baseline snapshot against new research run state and calculate sub-scores:
        - s_assumption: assumption invalidations
        - s_contradiction: claim additions & contradictions
        - s_matrix: decision option score drifts / recommendation flips
        - s_source: source reliability changes / untrusted sources
        """
        baseline_claims = baseline.claims_snapshot or []
        baseline_sources = baseline.sources_snapshot or []
        baseline_assumptions = baseline.assumptions_snapshot or []
        baseline_decision = baseline.decision_snapshot or {}

        curr_claims = current_state.get("claims") or []
        curr_sources = current_state.get("sources") or []
        curr_assumptions = current_state.get("assumptions") or []
        curr_decision = current_state.get("decision") or {}

        # 1. Assumption Invalidations (S_assumption)
        s_assumption = 0.0
        invalidated_assumptions: List[Dict[str, Any]] = []

        if baseline_assumptions:
            inv_count = 0
            curr_invalidated_texts = set(
                current_state.get("invalidated_assumptions") or []
            )
            for curr_a in curr_assumptions:
                if isinstance(curr_a, dict) and curr_a.get("status") in ["INVALIDATED", "REJECTED"]:
                    curr_invalidated_texts.add(curr_a.get("text") or curr_a.get("key"))

            for base_a in baseline_assumptions:
                a_text = base_a.get("text") if isinstance(base_a, dict) else str(base_a)
                if a_text in curr_invalidated_texts or (
                    isinstance(base_a, dict) and base_a.get("status") in ["INVALIDATED", "REJECTED"]
                ):
                    inv_count += 1
                    invalidated_assumptions.append({"text": a_text, "status": "INVALIDATED"})

            s_assumption = min(1.0, inv_count / max(1, len(baseline_assumptions)))
        elif current_state.get("invalidated_assumptions"):
            s_assumption = min(1.0, len(current_state.get("invalidated_assumptions") or []) * 0.5)

        # 2. Claim Contradictions & Additions (S_contradiction)
        s_contradiction = 0.0
        claims_added: List[Dict[str, Any]] = []
        claims_contradicted: List[Dict[str, Any]] = []

        curr_contradictions = current_state.get("contradictions") or []
        new_claims = current_state.get("new_claims") or []

        if curr_contradictions or new_claims:
            contradiction_count = len(curr_contradictions)
            new_claim_count = len(new_claims)
            total_claims = max(1, len(baseline_claims) + new_claim_count)
            s_contradiction = min(
                1.0, (contradiction_count * 0.4 + new_claim_count * 0.1) / total_claims
            )
            claims_contradicted = curr_contradictions
            claims_added = new_claims
        elif curr_claims and baseline_claims:
            base_texts = {c.get("content", "") for c in baseline_claims if isinstance(c, dict)}
            for c in curr_claims:
                c_text = c.get("content", "") if isinstance(c, dict) else str(c)
                if c_text and c_text not in base_texts:
                    claims_added.append({"content": c_text})
                if isinstance(c, dict) and c.get("status") in ["CONTRADICTED", "CONTESTED"]:
                    claims_contradicted.append(c)

            cnt = len(claims_contradicted) * 0.5 + len(claims_added) * 0.1
            s_contradiction = min(1.0, cnt / max(1, len(baseline_claims)))

        # Direct explicit override if passed in current_state sub_scores
        if "s_contradiction" in current_state and current_state["s_contradiction"] is not None:
            s_contradiction = _safe_float(current_state["s_contradiction"])

        # 3. Decision Option Score Drift / Recommendation Flip (S_matrix)
        s_matrix = 0.0
        recommendation_flipped = False
        base_rec = baseline_decision.get("recommendation")
        curr_rec = curr_decision.get("recommendation")

        if base_rec and curr_rec and base_rec != curr_rec:
            recommendation_flipped = True
            s_matrix = 1.0
        elif current_state.get("recommendation_flipped"):
            recommendation_flipped = True
            s_matrix = 1.0
        elif "score_drift" in current_state and current_state["score_drift"] is not None:
            s_matrix = min(1.0, max(0.0, _safe_float(current_state["score_drift"])))
        else:
            base_conf = _safe_float(baseline_decision.get("confidence"), 0.8)
            curr_conf = _safe_float(curr_decision.get("confidence"), 0.8)
            conf_drift = abs(base_conf - curr_conf)
            s_matrix = min(1.0, conf_drift * 2.0)

        # 4. Source Reliability Changes (S_source)
        s_source = 0.0
        sources_changed: List[Dict[str, Any]] = []

        untrusted_sources = current_state.get("untrusted_sources") or []
        if untrusted_sources:
            s_source = min(1.0, len(untrusted_sources) * 0.3)
            sources_changed = [{"url": u, "reason": "untrusted"} for u in untrusted_sources]
        elif curr_sources:
            low_quality_count = sum(
                1 for s in curr_sources if isinstance(s, dict) and _safe_float(s.get("quality_score"), 1.0) < 0.4
            )
            s_source = min(1.0, low_quality_count / max(1, len(curr_sources)))

        # Allow explicit override if provided in current_state sub_scores dict
        sub_scores_override = current_state.get("sub_scores") or {}
        if isinstance(sub_scores_override, dict):
            if "s_assumption" in sub_scores_override and sub_scores_override["s_assumption"] is not None:
                s_assumption = _safe_float(sub_scores_override["s_assumption"])
            if "s_contradiction" in sub_scores_override and sub_scores_override["s_contradiction"] is not None:
                s_contradiction = _safe_float(sub_scores_override["s_contradiction"])
            if "s_matrix" in sub_scores_override and sub_scores_override["s_matrix"] is not None:
                s_matrix = _safe_float(sub_scores_override["s_matrix"])
            if "s_source" in sub_scores_override and sub_scores_override["s_source"] is not None:
                s_source = _safe_float(sub_scores_override["s_source"])

        s_assumption = round(max(0.0, min(1.0, s_assumption)), 4)
        s_contradiction = round(max(0.0, min(1.0, s_contradiction)), 4)
        s_matrix = round(max(0.0, min(1.0, s_matrix)), 4)
        s_source = round(max(0.0, min(1.0, s_source)), 4)

        summary_parts = []
        if recommendation_flipped:
            summary_parts.append(f"Recommendation flipped from '{base_rec}' to '{curr_rec}'")
        if invalidated_assumptions:
            summary_parts.append(f"{len(invalidated_assumptions)} assumption(s) invalidated")
        if claims_contradicted:
            summary_parts.append(f"{len(claims_contradicted)} claim contradiction(s) found")
        if claims_added:
            summary_parts.append(f"{len(claims_added)} new claim(s) added")

        summary = "; ".join(summary_parts) if summary_parts else "No significant delta detected."

        return {
            "sub_scores": {
                "s_assumption": s_assumption,
                "s_contradiction": s_contradiction,
                "s_matrix": s_matrix,
                "s_source": s_source,
            },
            "diffs": {
                "claims_added": claims_added,
                "claims_contradicted": claims_contradicted,
                "sources_changed": sources_changed,
                "assumptions_invalidated": invalidated_assumptions,
                "decision_drift": {
                    "baseline_recommendation": base_rec,
                    "current_recommendation": curr_rec,
                    "recommendation_flipped": recommendation_flipped,
                },
            },
            "recommendation_flipped": recommendation_flipped,
            "summary": summary,
        }
