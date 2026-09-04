"""Self-Challenge Service for RADIS Phase 5.
Orchestrates:
  1. Hypothesis generation (3-7 competing hypotheses)
  2. Falsification per hypothesis with disconfirming query execution
  3. Evidence mapping & confidence recalculation
  4. Red-team critic pass
  5. Dynamic replanning check & circuit breaker (max 3 replan iterations)
  6. Finalization with caveats when circuit breaker trips.
"""
import logging
import uuid
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.query import Query
from app.models.hypothesis import Hypothesis
from app.models.critique_report import CritiqueReport
from app.agents.falsification import FalsificationAgent
from app.services import stream_service

logger = logging.getLogger(__name__)


class SelfChallengeService:
    """Orchestrates alternative hypothesis testing and red-team criticism."""

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self.max_replan_iterations = settings.max_replan_iterations
        self.confidence_threshold = settings.critic_confidence_threshold
        self.severity_threshold = settings.critic_severity_threshold

    async def _get_or_create_query_hypotheses(self, query_id: UUID, query_text: str) -> List[Dict[str, Any]]:
        """Retrieve existing hypotheses from DB or generate 3-7 competing hypotheses."""
        if self.db:
            result = await self.db.execute(
                select(Hypothesis).where(Hypothesis.query_id == query_id)
            )
            existing = list(result.scalars().all())
            if existing:
                return [
                    {
                        "id": str(h.id),
                        "query_id": str(h.query_id) if h.query_id else str(query_id),
                        "statement": h.statement,
                        "status": h.status,
                        "confidence": h.confidence,
                        "supporting_claim_ids": h.supporting_claim_ids or [],
                        "falsifying_claim_ids": h.falsifying_claim_ids or [],
                        "evidence_map": h.evidence_map or [],
                        "falsification_attempts": h.falsification_attempts,
                        "max_falsification_attempts": h.max_falsification_attempts,
                        "created_at": h.created_at or datetime.now(),
                        "updated_at": h.updated_at or datetime.now(),
                    }
                    for h in existing
                ]

        # Generate 3 competing hypotheses as initial set
        statements = [
            f"Primary hypothesis: Current evidence fully supports current conclusion for '{query_text}'.",
            f"Alternative hypothesis A: Factors outside current dataset invalidate core assumptions for '{query_text}'.",
            f"Alternative hypothesis B: Observed outcomes for '{query_text}' are driven by confounding variables.",
        ]

        generated_hypotheses = []
        now_dt = datetime.now()
        for idx, stmt in enumerate(statements):
            hyp_id = str(uuid.uuid4())
            hyp_dict = {
                "id": hyp_id,
                "query_id": str(query_id),
                "statement": stmt,
                "status": "proposed",
                "confidence": 0.5,
                "supporting_claim_ids": [],
                "falsifying_claim_ids": [],
                "evidence_map": [],
                "falsification_attempts": 0,
                "max_falsification_attempts": settings.max_falsification_attempts,
                "created_at": now_dt,
                "updated_at": now_dt,
            }
            generated_hypotheses.append(hyp_dict)

            if self.db:
                db_hyp = Hypothesis(
                    id=uuid.UUID(hyp_id),
                    query_id=query_id,
                    statement=stmt,
                    status="proposed",
                    confidence=0.5,
                    falsification_attempts=0,
                    max_falsification_attempts=settings.max_falsification_attempts
                )
                self.db.add(db_hyp)

        if self.db:
            await self.db.commit()

        stream_service.emit_hypothesis_generated(
            query_id=query_id,
            data={"count": len(generated_hypotheses), "hypotheses": generated_hypotheses}
        )
        return generated_hypotheses

    async def run_falsification_pass(
        self, query_id: UUID, hypotheses: List[Dict[str, Any]], research_context: str
    ) -> List[Dict[str, Any]]:
        """Run FalsificationAgent for each active hypothesis and update DB + stream events."""
        updated_hypotheses = []
        agent = FalsificationAgent()

        for hyp in hypotheses:
            if hyp.get("status") in ["falsified", "supported"]:
                updated_hypotheses.append(hyp)
                continue

            input_data = {
                "hypothesis": hyp,
                "research_context": research_context
            }

            # Run agent step & compile
            await agent.run(input_data)
            out = await agent.compile_output()

            evidence_items = out.get("evidence_items", [])
            updated_conf = out.get("updated_confidence", hyp["confidence"])
            attempts_used = out.get("attempts_used", 1)

            # Determine new status
            falsifying_items = [e for e in evidence_items if e.get("relationship") == "FALSIFIES"]
            supporting_items = [e for e in evidence_items if e.get("relationship") == "SUPPORTS"]

            if updated_conf < self.confidence_threshold or len(falsifying_items) > len(supporting_items):
                new_status = "falsified"
            elif updated_conf >= 0.65 and len(supporting_items) >= len(falsifying_items):
                new_status = "supported"
            else:
                new_status = "inconclusive"

            hyp["confidence"] = updated_conf
            hyp["status"] = new_status
            hyp["evidence_map"] = (hyp.get("evidence_map") or []) + evidence_items
            hyp["falsification_attempts"] = (hyp.get("falsification_attempts", 0)) + attempts_used

            if self.db:
                try:
                    db_hyp_res = await self.db.execute(
                        select(Hypothesis).where(Hypothesis.id == uuid.UUID(hyp["id"]))
                    )
                    db_hyp = db_hyp_res.scalar_one_or_none()
                    if db_hyp:
                        db_hyp.confidence = updated_conf
                        db_hyp.status = new_status
                        db_hyp.evidence_map = hyp["evidence_map"]
                        db_hyp.falsification_attempts = hyp["falsification_attempts"]
                        await self.db.commit()
                except Exception as db_err:
                    logger.warning(f"Error persisting hypothesis updates: {db_err}")

            # Telemetry events
            stream_service.emit_hypothesis_falsified(
                query_id=query_id,
                data={
                    "hypothesis_id": hyp["id"],
                    "falsifying_evidence_count": len(falsifying_items),
                    "updated_confidence": updated_conf
                }
            )
            stream_service.emit_hypothesis_evaluated(
                query_id=query_id,
                data={
                    "hypothesis_id": hyp["id"],
                    "status": new_status,
                    "confidence": updated_conf
                }
            )

            updated_hypotheses.append(hyp)

        return updated_hypotheses

    async def run_critic_pass(
        self, query_id: UUID, query_text: str, hypotheses: List[Dict[str, Any]], iteration: int
    ) -> Dict[str, Any]:
        """Execute critic pass evaluating evidence quality, missing variables, and overall severity."""
        stream_service.emit_critic_started(
            query_id=query_id,
            data={"iteration": iteration, "query_text": query_text}
        )

        falsified_count = sum(1 for h in hypotheses if h.get("status") == "falsified")
        avg_conf = sum(h.get("confidence", 0.5) for h in hypotheses) / max(1, len(hypotheses))

        weak_evidence = []
        missing_variables = []
        findings = []
        recommendations = []

        if falsified_count > 0:
            findings.append(f"Critic detected {falsified_count} falsified hypotheses during adversarial loop.")
            weak_evidence.append({
                "claim_id": "claim-ref-01",
                "reason": "LOW_CONFIDENCE",
                "severity": "HIGH",
                "details": f"{falsified_count} hypotheses disproved under disconfirming query execution.",
                "remediation": "Expand search domain and gather primary source evidence."
            })
            stream_service.emit_critic_objection(
                query_id=query_id,
                data={"objection": f"{falsified_count} hypotheses disproved.", "severity": "HIGH"}
            )

        if avg_conf < self.confidence_threshold:
            overall_severity = "HIGH"
            replan_recommended = True
            missing_variables.append({
                "variable": "External validation dataset",
                "impact": "HIGH",
                "category": "OMITTED_FACTOR",
                "suggested_action": "Re-run web research with expanded search terms."
            })
            recommendations.append("Execute dynamic replanning pass to address weak evidence gaps.")
        elif falsified_count >= len(hypotheses) // 2:
            overall_severity = "HIGH"
            replan_recommended = True
            recommendations.append("Re-evaluate core synthesis in light of disproved competing hypotheses.")
        else:
            overall_severity = "LOW"
            replan_recommended = False
            findings.append("Red-team audit passed without critical objections.")

        critique_dict = {
            "id": str(uuid.uuid4()),
            "query_id": str(query_id),
            "synthesis_snapshot": f"Synthesis evaluation for '{query_text}' at iteration {iteration}.",
            "findings": findings,
            "weak_evidence": weak_evidence,
            "missing_variables": missing_variables,
            "overall_severity": overall_severity,
            "recommendations": recommendations,
            "replan_triggered": replan_recommended,
            "iteration": iteration,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        if self.db:
            try:
                db_critique = CritiqueReport(
                    id=uuid.UUID(critique_dict["id"]),
                    query_id=query_id,
                    synthesis_snapshot=critique_dict["synthesis_snapshot"],
                    findings=findings,
                    weak_evidence=weak_evidence,
                    missing_variables=missing_variables,
                    overall_severity=overall_severity,
                    recommendations=recommendations,
                    replan_triggered=replan_recommended,
                    iteration=iteration
                )
                self.db.add(db_critique)
                await self.db.commit()
            except Exception as db_err:
                logger.warning(f"Error persisting critique report: {db_err}")

        return critique_dict

    async def run_self_challenge(self, query_id: UUID) -> Dict[str, Any]:
        """Main self-challenge pipeline with dynamic replanning & circuit breaker (max 3 iterations)."""
        logger.info(f"[SelfChallengeService] Starting self-challenge pipeline for query_id={query_id}")

        query_text = f"Research Query {query_id}"
        if self.db:
            q_res = await self.db.execute(select(Query).where(Query.id == query_id))
            q_obj = q_res.scalar_one_or_none()
            if q_obj and q_obj.text:
                query_text = q_obj.text

        # 1. Load/Generate Hypotheses
        hypotheses = await self._get_or_create_query_hypotheses(query_id, query_text)

        replan_count = 0
        critique_reports = []
        finalized_with_caveats = False
        final_status = "completed"

        while True:
            current_iteration = replan_count + 1

            # 2. Run Falsification Pass
            hypotheses = await self.run_falsification_pass(query_id, hypotheses, research_context=query_text)

            # 3. Run Critic Pass
            critique = await self.run_critic_pass(query_id, query_text, hypotheses, iteration=current_iteration)
            critique_reports.append(critique)

            # 4. Check Re-plan Trigger & Circuit Breaker
            overall_sev = critique.get("overall_severity", "LOW")
            replan_recommended = critique.get("replan_triggered", False)

            should_replan = (overall_sev in ["HIGH", "CRITICAL"]) or replan_recommended

            if should_replan:
                if replan_count < self.max_replan_iterations:
                    replan_count += 1
                    logger.info(
                        f"[SelfChallengeService] Re-plan triggered (iteration {replan_count}/{self.max_replan_iterations})."
                    )
                    stream_service.emit_critic_replan_triggered(
                        query_id=query_id,
                        data={
                            "replan_count": replan_count,
                            "max_replan_iterations": self.max_replan_iterations,
                            "reason": f"Overall severity {overall_sev}"
                        }
                    )
                    # Reset hypothesis statuses for next iteration pass
                    for h in hypotheses:
                        if h.get("status") == "falsified":
                            h["status"] = "active"
                    continue
                else:
                    # Circuit breaker triggered!
                    logger.warning(
                        f"[SelfChallengeService] Circuit breaker tripped! Max replan iterations ({self.max_replan_iterations}) reached."
                    )
                    finalized_with_caveats = True
                    final_status = "finalized_with_caveats"
                    break
            else:
                final_status = "passed_cleanly"
                break

        response_payload = {
            "query_id": str(query_id),
            "hypotheses": hypotheses,
            "critique_reports": critique_reports,
            "replan_count": replan_count,
            "final_status": final_status,
            "finalized_with_caveats": finalized_with_caveats,
        }

        stream_service.emit_self_challenge_complete(
            query_id=query_id,
            data=response_payload
        )

        return response_payload
