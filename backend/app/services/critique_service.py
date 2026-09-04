"""Critique Service for Phase 5.
Manages running critic passes, persisting critique reports, querying reports,
and evaluating re-planning trigger conditions.
"""
from uuid import UUID
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.query import Query
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.critique_report import CritiqueReport
from app.agents.critic import CriticAgent
from app.agents.agent_contracts import CriticInput
from app.config import settings
from app.services.stream_service import stream_service, StreamEvent

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4
}


class CritiqueService:
    """Service to execute red-team critique passes and manage critique reports."""

    async def run_critique(self, db: AsyncSession, query_id: UUID) -> CritiqueReport:
        """Runs an independent red-team critique pass on the query's current synthesis and claims."""
        logger.info(f"[CritiqueService] Initiating critique pass for query_id {query_id}")

        # Fetch query
        if hasattr(db, "query"):
            query = db.query(Query).filter(Query.id == query_id).first()
        else:
            result = await db.execute(select(Query).where(Query.id == query_id))
            query = result.scalar_one_or_none()

        if not query:
            raise ValueError(f"Query with id {query_id} not found.")

        # Fetch associated claims
        if hasattr(db, "query"):
            claims = db.query(Claim).filter(Claim.query_id == query_id).all()
        else:
            claims_res = await db.execute(select(Claim).where(Claim.query_id == query_id))
            claims = claims_res.scalars().all()

        # Fetch associated evidence
        if hasattr(db, "query"):
            evidence_list = db.query(Evidence).filter(Evidence.query_id == query_id).all()
        else:
            ev_res = await db.execute(select(Evidence).where(Evidence.query_id == query_id))
            evidence_list = ev_res.scalars().all()



        # Prepare CriticInput
        claims_data = [
            {
                "id": str(c.id),
                "content": c.content,
                "confidence": c.confidence,
                "status": c.status,
                "claim_type": c.claim_type
            }
            for c in claims
        ]
        evidence_chain = [
            {"id": str(e.id), "content": e.content, "confidence": e.confidence}
            for e in evidence_list
        ]

        critic_input = CriticInput(
            synthesis=query.summary or "",
            claims=claims_data,
            evidence_chain=evidence_chain,
            hypotheses=[]
        )

        # Run agent
        critic_agent = CriticAgent()
        output = await critic_agent.run(critic_input.model_dump())

        # Determine iteration number
        count_res = await db.execute(
            select(func.count(CritiqueReport.id)).where(CritiqueReport.query_id == query_id)
        )
        existing_count = count_res.scalar() or 0
        iteration = existing_count + 1

        # Evaluate replan trigger condition
        replan_triggered = self.should_trigger_replan(output, settings)

        # Persist report
        report = CritiqueReport(
            query_id=query_id,
            synthesis_snapshot=query.summary or "",
            findings=output.get("findings", []),
            weak_evidence=output.get("weak_evidence", []),
            missing_variables=output.get("missing_variables", []),
            overall_severity=output.get("overall_severity", "LOW"),
            recommendations=output.get("recommendations", []),
            replan_triggered=replan_triggered,
            iteration=iteration
        )
        db.add(report)
        commit_res = db.commit()
        if hasattr(commit_res, "__await__"):
            await commit_res
        refresh_res = db.refresh(report)
        if hasattr(refresh_res, "__await__"):
            await refresh_res


        # Broadcast SSE telemetry
        event_type = "critic:replan_triggered" if replan_triggered else "critic:complete"
        stream_service.publish(
            query_id,
            StreamEvent(
                event_type=event_type,
                data={
                    "query_id": str(query_id),
                    "report_id": str(report.id),
                    "overall_severity": report.overall_severity,
                    "replan_triggered": replan_triggered,
                    "iteration": iteration,
                    "weak_evidence_count": len(report.weak_evidence),
                    "missing_variables_count": len(report.missing_variables),
                },
                timestamp=datetime.now()
            )
        )

        logger.info(
            f"[CritiqueService] Critique report {report.id} created for query {query_id}. "
            f"Severity: {report.overall_severity}, Replan: {replan_triggered}"
        )
        return report

    async def get_critiques(self, db: AsyncSession, query_id: UUID) -> List[CritiqueReport]:
        """Queries all critique reports for a specific query ordered by iteration."""
        result = await db.execute(
            select(CritiqueReport)
            .where(CritiqueReport.query_id == query_id)
            .order_by(CritiqueReport.iteration.asc())
        )
        return list(result.scalars().all())

    get_critiques_by_query = get_critiques


    @staticmethod
    def should_trigger_replan(report: Any, config: Any = settings) -> bool:
        """Evaluates whether a critique report or critic output should trigger a re-plan.
        
        Triggers True if:
        1. overall_severity >= config.critic_severity_threshold (e.g. HIGH or CRITICAL)
        2. OR any weak_evidence item has severity == 'CRITICAL'
        3. OR any hypothesis confidence < config.critic_confidence_threshold (default 0.3)
        """
        if hasattr(report, "model_dump"):
            report_dict = report.model_dump()
        elif isinstance(report, dict):
            report_dict = report
        else:
            report_dict = {
                "overall_severity": getattr(report, "overall_severity", "LOW"),
                "weak_evidence": getattr(report, "weak_evidence", []),
                "replan_recommended": getattr(report, "replan_recommended", False),
            }

        severity = str(report_dict.get("overall_severity", "LOW")).upper()
        threshold = getattr(config, "critic_severity_threshold", "HIGH").upper()

        sev_val = SEVERITY_WEIGHTS.get(severity, 1)
        thresh_val = SEVERITY_WEIGHTS.get(threshold, 3)

        # 1. Severity threshold check
        if sev_val >= thresh_val:
            return True

        # 2. Critical weak evidence check
        weak_evidence = report_dict.get("weak_evidence", [])
        if any(isinstance(w, dict) and w.get("severity") == "CRITICAL" for w in weak_evidence):
            return True

        # 3. Explicit replan recommendation flag
        if report_dict.get("replan_recommended", False):
            return True

        return False


critique_service = CritiqueService()
