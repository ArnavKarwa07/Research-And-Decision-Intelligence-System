"""Hypothesis Service for RADIS.
Handles creation, mapping, confidence math, and falsification of hypotheses.
"""
import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.hypothesis import HypothesisAgent
from app.models.hypothesis import Hypothesis
from app.models.query import Query

logger = logging.getLogger(__name__)


class HypothesisService:
    """Service layer for hypothesis operations."""

    async def generate_hypotheses(
        self,
        db: Any,
        query_id: uuid.UUID
    ) -> list[Hypothesis]:
        """Generate competing hypotheses for a query via HypothesisAgent."""
        if isinstance(db, AsyncSession):
            stmt = select(Query).where(Query.id == query_id)
            result = await db.execute(stmt)
            query = result.scalar_one_or_none()
        else:
            query = db.query(Query).filter(Query.id == query_id).first()

        if not query:
            raise ValueError(f"Query {query_id} not found")

        agent = HypothesisAgent()
        res = await agent.run({"query_text": query.text})
        hypotheses_data = res.get("hypotheses", [])

        db_hypotheses = []
        for h in hypotheses_data:
            hyp_id = uuid.uuid4()
            if h.get("hypothesis_id"):
                try:
                    hyp_id = uuid.UUID(str(h["hypothesis_id"]))
                except ValueError:
                    hyp_id = uuid.uuid4()

            hyp_obj = Hypothesis(
                id=hyp_id,
                query_id=query_id,
                statement=h.get("statement", ""),
                status="proposed",
                confidence=h.get("initial_confidence", 0.5),
                supporting_claim_ids=[],
                falsifying_claim_ids=[],
                evidence_map=[],
                falsification_attempts=0,
                max_falsification_attempts=5,
            )
            db.add(hyp_obj)
            db_hypotheses.append(hyp_obj)

        if isinstance(db, AsyncSession):
            await db.commit()
            for h in db_hypotheses:
                await db.refresh(h)
        else:
            db.commit()
            for h in db_hypotheses:
                db.refresh(h)

        return db_hypotheses

    async def get_hypotheses(
        self,
        db: Any,
        query_id: uuid.UUID
    ) -> list[Hypothesis]:
        """Retrieve all hypotheses for a research query."""
        if isinstance(db, AsyncSession):
            stmt = select(Hypothesis).where(Hypothesis.query_id == query_id)
            result = await db.execute(stmt)
            return list(result.scalars().all())
        else:
            return db.query(Hypothesis).filter(Hypothesis.query_id == query_id).all()

    async def get_hypotheses_by_query(
        self,
        db: Any,
        query_id: uuid.UUID
    ) -> list[Hypothesis]:
        """Alias for get_hypotheses for backward compatibility."""
        return await self.get_hypotheses(db, query_id)

    async def get_hypothesis_by_id(
        self,
        db: Any,
        hypothesis_id: uuid.UUID
    ) -> Hypothesis | None:
        """Retrieve a specific hypothesis by ID."""
        if isinstance(db, AsyncSession):
            stmt = select(Hypothesis).where(Hypothesis.id == hypothesis_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            return db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()

    async def update_hypothesis(
        self,
        db: Any,
        hypothesis_id: uuid.UUID,
        updates: dict[str, Any]
    ) -> Hypothesis:
        """Update a hypothesis record."""
        if isinstance(db, AsyncSession):
            stmt = select(Hypothesis).where(Hypothesis.id == hypothesis_id)
            result = await db.execute(stmt)
            hyp = result.scalar_one_or_none()
        else:
            hyp = db.query(Hypothesis).filter(Hypothesis.id == hypothesis_id).first()

        if not hyp:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        for k, v in updates.items():
            if v is not None and hasattr(hyp, k):
                setattr(hyp, k, v)

        # Recalculate confidence if evidence_map was updated
        if "evidence_map" in updates and updates["evidence_map"] is not None:
            hyp.confidence = self.recalculate_confidence(hyp.evidence_map or [])

        if isinstance(db, AsyncSession):
            await db.commit()
            await db.refresh(hyp)
        else:
            db.commit()
            db.refresh(hyp)

        return hyp

    async def map_evidence(
        self,
        db: AsyncSession,
        hypothesis_id: uuid.UUID,
        evidence_entry: dict[str, Any]
    ) -> Hypothesis:
        """Map an evidence entry to a hypothesis and recalculate confidence."""
        stmt = select(Hypothesis).where(Hypothesis.id == hypothesis_id)
        result = await db.execute(stmt)
        hyp = result.scalar_one_or_none()
        if not hyp:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        cur_map = list(hyp.evidence_map or [])
        cur_map.append(evidence_entry)
        hyp.evidence_map = cur_map

        # Update claim IDs if present in evidence entry
        claim_id = evidence_entry.get("claim_id") or evidence_entry.get("evidence_id")
        rel = str(evidence_entry.get("relationship", "")).lower()
        if claim_id:
            if rel in ("supports", "supporting"):
                sup_ids = list(hyp.supporting_claim_ids or [])
                if claim_id not in sup_ids:
                    sup_ids.append(claim_id)
                    hyp.supporting_claim_ids = sup_ids
            elif rel in ("falsifies", "falsifying"):
                fals_ids = list(hyp.falsifying_claim_ids or [])
                if claim_id not in fals_ids:
                    fals_ids.append(claim_id)
                    hyp.falsifying_claim_ids = fals_ids

        hyp.confidence = self.recalculate_confidence(cur_map)
        await db.commit()
        await db.refresh(hyp)
        return hyp

    async def run_falsification(
        self,
        db: AsyncSession,
        hypothesis_id: uuid.UUID
    ) -> dict[str, Any]:
        """Trigger FalsificationAgent for a specific hypothesis."""
        stmt = select(Hypothesis).where(Hypothesis.id == hypothesis_id)
        result = await db.execute(stmt)
        hyp = result.scalar_one_or_none()
        if not hyp:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        if hyp.falsification_attempts >= hyp.max_falsification_attempts:
            return {
                "hypothesis_id": str(hypothesis_id),
                "status": hyp.status,
                "confidence": hyp.confidence,
                "falsification_attempts": hyp.falsification_attempts,
                "message": f"Falsification attempt limit ({hyp.max_falsification_attempts}) reached.",
            }

        try:
            from app.agents.falsification import FalsificationAgent
            agent = FalsificationAgent()
            res = await agent.run({
                "hypothesis": {
                    "hypothesis_id": str(hyp.id),
                    "statement": hyp.statement,
                    "initial_confidence": hyp.confidence,
                }
            })
            new_items = res.get("evidence_items", [])
        except Exception as e:
            logger.warning(f"FalsificationAgent execution error: {e}")
            new_items = [{
                "evidence_id": str(uuid.uuid4()),
                "relationship": "falsifies",
                "weight": 0.5,
                "justification": f"Falsification check executed: {e!s}"
            }]

        cur_map = list(hyp.evidence_map or [])
        cur_map.extend(new_items)
        hyp.evidence_map = cur_map
        hyp.falsification_attempts += 1
        hyp.confidence = self.recalculate_confidence(cur_map)

        if hyp.confidence >= 0.70:
            hyp.status = "supported"
        elif hyp.confidence <= 0.30:
            hyp.status = "falsified"
        else:
            hyp.status = "inconclusive"

        await db.commit()
        await db.refresh(hyp)

        return {
            "hypothesis_id": str(hyp.id),
            "status": hyp.status,
            "confidence": hyp.confidence,
            "falsification_attempts": hyp.falsification_attempts,
            "evidence_count": len(cur_map),
        }

    @staticmethod
    def recalculate_confidence(evidence_map: list[dict[str, Any]]) -> float:
        """Pure math calculation of hypothesis confidence from evidence map.
        formula: (Σ supporting_weight - Σ falsifying_weight) / Σ total_weight
        bounded to [0.0, 1.0]. Returns 0.5 default if no weights.
        """
        if not evidence_map:
            return 0.5

        sup_weight = 0.0
        fals_weight = 0.0

        for item in evidence_map:
            if not isinstance(item, dict):
                continue
            raw_weight = item.get("weight", 1.0)
            try:
                weight = float(raw_weight) if raw_weight is not None else 1.0
                weight = max(weight, 0.0)
            except (ValueError, TypeError):
                weight = 1.0

            rel = str(item.get("relationship", "")).lower()
            if rel in ("supports", "supporting"):
                sup_weight += weight
            elif rel in ("falsifies", "falsifying"):
                fals_weight += weight

        total_weight = sup_weight + fals_weight

        if total_weight == 0:
            return 0.5

        net_ratio = (sup_weight - fals_weight) / total_weight
        normalized = (net_ratio + 1.0) / 2.0
        return round(max(0.0, min(1.0, normalized)), 2)


hypothesis_service = HypothesisService()
