"""
Human-in-the-Loop (HITL) Service (Phase 8).
Manages Approval Gates, Clarifications, 5-Minute Auto-Kill Timeout Events, Evidence Corrections, and Assumption Confirmations.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.approval_gate import ApprovalGate, ApprovalGateStatus, RiskLevel
from app.models.clarification import ClarificationQuestion, ClarificationStatus
from app.models.claim import Claim
from app.models.hypothesis import Hypothesis
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class HITLService:
    @staticmethod
    def create_approval_gate(
        db: Session,
        run_id: str,
        agent_id: str,
        tool_name: str,
        tool_args: Optional[Dict[str, Any]] = None,
        risk_level: str = RiskLevel.HIGH.value,
        description: str = "High-risk action requiring human approval.",
        timeout_seconds: int = 300,  # 5-minute auto-kill timeout
    ) -> ApprovalGate:
        """Create a new pending approval gate."""
        # Scrub PII from tool args before storing in gate
        clean_args, _, _ = SecurityService.scan_and_redact_pii(tool_args or {})

        gate = ApprovalGate(
            run_id=run_id,
            agent_id=agent_id,
            tool_name=tool_name,
            tool_args=clean_args,
            risk_level=risk_level,
            description=description,
            status=ApprovalGateStatus.PENDING.value,
            timeout_seconds=timeout_seconds,
            created_at=datetime.now(timezone.utc),
        )
        db.add(gate)
        db.commit()
        db.refresh(gate)

        SecurityService.log_audit_event(
            db=db,
            action_type="approval_requested",
            severity="WARNING",
            run_id=run_id,
            agent_id=agent_id,
            details={
                "gate_id": gate.id,
                "tool_name": tool_name,
                "risk_level": risk_level,
                "timeout_seconds": timeout_seconds,
            },
        )
        return gate

    @staticmethod
    def check_and_apply_timeouts(db: Session, run_id: Optional[str] = None) -> int:
        """
        Check for pending approval gates and clarification questions older than their timeout (default 5 mins / 300s).
        Automatically transitions expired gates/clarifications to EXPIRED status and logs audit event.
        Returns: total count of timed-out events killed.
        """
        now = datetime.now(timezone.utc)
        timed_out_count = 0

        # Query pending approval gates
        query_gates = db.query(ApprovalGate).filter(ApprovalGate.status == ApprovalGateStatus.PENDING.value)
        if run_id:
            query_gates = query_gates.filter(ApprovalGate.run_id == run_id)

        pending_gates = query_gates.all()
        for gate in pending_gates:
            created_at = gate.created_at
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            cutoff = created_at + timedelta(seconds=gate.timeout_seconds) if created_at else now
            if now >= cutoff:
                gate.status = ApprovalGateStatus.EXPIRED.value
                gate.resolved_at = now
                gate.user_feedback = "Auto-killed by 5-minute timeout."
                timed_out_count += 1

                SecurityService.log_audit_event(
                    db=db,
                    action_type="approval_auto_killed_timeout",
                    severity="ERROR",
                    run_id=gate.run_id,
                    agent_id=gate.agent_id,
                    details={
                        "gate_id": gate.id,
                        "tool_name": gate.tool_name,
                        "timeout_seconds": gate.timeout_seconds,
                    },
                )

        # Query pending clarifications
        query_clarifications = db.query(ClarificationQuestion).filter(ClarificationQuestion.status == ClarificationStatus.PENDING.value)
        if run_id:
            query_clarifications = query_clarifications.filter(ClarificationQuestion.run_id == run_id)

        pending_clarifications = query_clarifications.all()
        for clar in pending_clarifications:
            created_at = clar.created_at
            if created_at and created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            cutoff = created_at + timedelta(seconds=300) if created_at else now  # 5 minutes
            if now >= cutoff:
                clar.status = ClarificationStatus.EXPIRED.value
                clar.resolved_at = now
                clar.answer = "Auto-killed by 5-minute timeout."
                timed_out_count += 1

                SecurityService.log_audit_event(
                    db=db,
                    action_type="clarification_auto_killed_timeout",
                    severity="ERROR",
                    run_id=clar.run_id,
                    agent_id=clar.agent_id,
                    details={"clarification_id": clar.id},
                )

        if timed_out_count > 0:
            db.commit()

        return timed_out_count

    @staticmethod
    def resolve_approval_gate(
        db: Session, gate_id: str, action: str, user_feedback: Optional[str] = None
    ) -> Optional[ApprovalGate]:
        """
        Resolve an approval gate with user decision ('approve', 'reject', or 'kill').
        """
        gate = db.query(ApprovalGate).filter(ApprovalGate.id == gate_id).first()
        if not gate:
            return None

        # Process automatic timeouts first
        HITLService.check_and_apply_timeouts(db, run_id=gate.run_id)

        if gate.status != ApprovalGateStatus.PENDING.value:
            return gate  # Already resolved or expired

        now = datetime.now(timezone.utc)
        if action.lower() == "approve":
            gate.status = ApprovalGateStatus.APPROVED.value
        elif action.lower() == "kill":
            gate.status = ApprovalGateStatus.EXPIRED.value
        else:
            gate.status = ApprovalGateStatus.REJECTED.value

        gate.resolved_at = now
        gate.user_feedback = user_feedback
        db.commit()
        db.refresh(gate)

        SecurityService.log_audit_event(
            db=db,
            action_type="approval_resolved",
            severity="INFO" if gate.status == ApprovalGateStatus.APPROVED.value else "WARNING",
            run_id=gate.run_id,
            agent_id=gate.agent_id,
            details={
                "gate_id": gate.id,
                "action": action,
                "status": gate.status,
                "user_feedback": user_feedback,
            },
        )
        return gate

    @staticmethod
    def create_clarification_question(
        db: Session,
        run_id: str,
        agent_id: str,
        prompt: str,
        options: Optional[List[str]] = None,
    ) -> ClarificationQuestion:
        """Create a clarification question to prompt the user."""
        clarification = ClarificationQuestion(
            run_id=run_id,
            agent_id=agent_id,
            prompt=prompt,
            options=options,
            status=ClarificationStatus.PENDING.value,
            created_at=datetime.now(timezone.utc),
        )
        db.add(clarification)
        db.commit()
        db.refresh(clarification)

        SecurityService.log_audit_event(
            db=db,
            action_type="clarification_requested",
            severity="INFO",
            run_id=run_id,
            agent_id=agent_id,
            details={"clarification_id": clarification.id, "prompt": prompt},
        )
        return clarification

    @staticmethod
    def answer_clarification_question(
        db: Session, clarification_id: str, answer: str
    ) -> Optional[ClarificationQuestion]:
        """Submit answer for a clarification question."""
        clarification = db.query(ClarificationQuestion).filter(ClarificationQuestion.id == clarification_id).first()
        if not clarification:
            return None

        if clarification.status != ClarificationStatus.PENDING.value:
            return clarification

        clarification.answer = answer
        clarification.status = ClarificationStatus.ANSWERED.value
        clarification.resolved_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(clarification)

        SecurityService.log_audit_event(
            db=db,
            action_type="clarification_answered",
            severity="INFO",
            run_id=clarification.run_id,
            agent_id=clarification.agent_id,
            details={"clarification_id": clarification.id, "answer": answer},
        )
        return clarification

    @staticmethod
    def override_claim_evidence(
        db: Session, claim_id: str, new_status: str, notes: Optional[str] = None
    ) -> Optional[Claim]:
        """Allow user to manually correct a claim's status or notes."""
        import uuid
        try:
            target_id = uuid.UUID(claim_id) if isinstance(claim_id, str) else claim_id
        except Exception:
            target_id = claim_id

        claim = db.query(Claim).filter(Claim.id == target_id).first()
        if not claim:
            return None

        claim.status = new_status
        meta = dict(claim.metadata_ or {})
        meta["user_override"] = True
        meta["user_notes"] = notes
        meta["user_updated_at"] = datetime.now(timezone.utc).isoformat()
        claim.metadata_ = meta
        db.commit()
        db.refresh(claim)
        return claim

    @staticmethod
    def confirm_hypothesis_assumption(
        db: Session, hypothesis_id: str, confirmed: bool, user_notes: Optional[str] = None
    ) -> Optional[Hypothesis]:
        """Confirm or reject a preliminary agent hypothesis/assumption."""
        import uuid
        try:
            target_id = uuid.UUID(hypothesis_id) if isinstance(hypothesis_id, str) else hypothesis_id
        except Exception:
            target_id = hypothesis_id

        hypothesis = db.query(Hypothesis).filter(Hypothesis.id == target_id).first()
        if not hypothesis:
            return None

        if confirmed:
            hypothesis.status = "confirmed"
        else:
            hypothesis.status = "rejected"

        hypothesis.falsification_plan = f"User decision: {'Confirmed' if confirmed else 'Rejected'}. Notes: {user_notes or 'None'}"
        db.commit()
        db.refresh(hypothesis)
        return hypothesis
