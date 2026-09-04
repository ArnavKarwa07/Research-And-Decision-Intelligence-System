"""
API router for Phase 8 Human-in-the-Loop (HITL) endpoints.
Endpoints for approval gates, clarifications, evidence editing, and assumption confirmations.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.approval_gate import ApprovalGate, ApprovalGateStatus
from app.models.clarification import ClarificationQuestion, ClarificationStatus
from app.schemas.hitl import (
    ApprovalGateCreate,
    ApprovalGateResolution,
    ApprovalGateResponse,
    ClarificationQuestionCreate,
    ClarificationAnswer,
    ClarificationResponse,
    EvidenceOverrideRequest,
    AssumptionConfirmationRequest,
)
from app.schemas.claim import ClaimResponse
from app.schemas.hypothesis import HypothesisResponse
from app.services.hitl_service import HITLService

router = APIRouter(prefix="/hitl", tags=["hitl"])


@router.get("/approvals", response_model=List[ApprovalGateResponse])
def list_approval_gates(run_id: Optional[str] = None, status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    """List pending or filtered approval gates, triggering auto-kill timeout check first."""
    HITLService.check_and_apply_timeouts(db, run_id=run_id)

    query = db.query(ApprovalGate)
    if run_id:
        query = query.filter(ApprovalGate.run_id == run_id)
    if status_filter:
        query = query.filter(ApprovalGate.status == status_filter)

    gates = query.order_by(ApprovalGate.created_at.desc()).all()
    return [gate.to_dict() for gate in gates]


@router.post("/approvals/{gate_id}/resolve", response_model=ApprovalGateResponse)
def resolve_approval_gate(gate_id: str, resolution: ApprovalGateResolution, db: Session = Depends(get_db)):
    """Approve, reject, or kill a pending approval gate."""
    gate = HITLService.resolve_approval_gate(
        db=db,
        gate_id=gate_id,
        action=resolution.action,
        user_feedback=resolution.user_feedback,
    )
    if not gate:
        raise HTTPException(status_code=404, detail=f"Approval gate '{gate_id}' not found.")
    return gate.to_dict()


@router.get("/clarifications", response_model=List[ClarificationResponse])
def list_clarifications(run_id: Optional[str] = None, status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    """List clarification questions, applying 5-minute timeout checks first."""
    HITLService.check_and_apply_timeouts(db, run_id=run_id)

    query = db.query(ClarificationQuestion)
    if run_id:
        query = query.filter(ClarificationQuestion.run_id == run_id)
    if status_filter:
        query = query.filter(ClarificationQuestion.status == status_filter)

    clarifications = query.order_by(ClarificationQuestion.created_at.desc()).all()
    return [clar.to_dict() for clar in clarifications]


@router.post("/clarifications/{question_id}/answer", response_model=ClarificationResponse)
def answer_clarification(question_id: str, answer_body: ClarificationAnswer, db: Session = Depends(get_db)):
    """Submit user answer to a clarification question."""
    clarification = HITLService.answer_clarification_question(
        db=db, clarification_id=question_id, answer=answer_body.answer
    )
    if not clarification:
        raise HTTPException(status_code=404, detail=f"Clarification question '{question_id}' not found.")
    return clarification.to_dict()


@router.post("/evidence/override")
def override_claim_evidence(payload: EvidenceOverrideRequest, db: Session = Depends(get_db)):
    """User evidence correction endpoint for modifying verified claims."""
    claim = HITLService.override_claim_evidence(
        db=db,
        claim_id=payload.claim_id,
        new_status=payload.status,
        notes=payload.notes,
    )
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim '{payload.claim_id}' not found.")
    return {"message": "Claim evidence status successfully overridden.", "claim_id": str(claim.id), "status": claim.status}


@router.post("/assumptions/confirm")
def confirm_assumption(payload: AssumptionConfirmationRequest, db: Session = Depends(get_db)):
    """User assumption confirmation or rejection endpoint."""
    hypothesis = HITLService.confirm_hypothesis_assumption(
        db=db,
        hypothesis_id=payload.hypothesis_id,
        confirmed=payload.confirmed,
        user_notes=payload.user_notes,
    )
    if not hypothesis:
        raise HTTPException(status_code=404, detail=f"Hypothesis '{payload.hypothesis_id}' not found.")
    return {
        "message": "Assumption updated successfully.",
        "hypothesis_id": str(hypothesis.id),
        "status": hypothesis.status,
    }
