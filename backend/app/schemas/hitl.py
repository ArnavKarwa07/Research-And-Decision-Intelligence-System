"""
Pydantic schemas for Human-in-the-Loop Approval Gates & Clarifications (Phase 8).
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ApprovalGateCreate(BaseModel):
    run_id: str
    agent_id: str
    tool_name: str
    tool_args: Optional[Dict[str, Any]] = None
    risk_level: str = "high"
    description: str
    timeout_seconds: int = 300  # 5 minutes auto-kill timeout default


class ApprovalGateResolution(BaseModel):
    action: str = Field(..., description="approve, reject, or kill")
    user_feedback: Optional[str] = None


class ApprovalGateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    agent_id: str
    tool_name: str
    tool_args: Optional[Dict[str, Any]] = None
    risk_level: str
    description: str
    status: str
    user_feedback: Optional[str] = None
    timeout_seconds: int
    created_at: str
    resolved_at: Optional[str] = None


class ClarificationQuestionCreate(BaseModel):
    run_id: str
    agent_id: str
    prompt: str
    options: Optional[List[str]] = None


class ClarificationAnswer(BaseModel):
    answer: str


class ClarificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    agent_id: str
    prompt: str
    options: Optional[List[str]] = None
    answer: Optional[str] = None
    status: str
    created_at: str
    resolved_at: Optional[str] = None



class EvidenceOverrideRequest(BaseModel):
    claim_id: str
    status: str = Field(..., description="supported, contradicted, inferred, unverified")
    notes: Optional[str] = None
    weight_adjustment: Optional[float] = Field(1.0, ge=0.0, le=5.0)


class AssumptionConfirmationRequest(BaseModel):
    hypothesis_id: str
    confirmed: bool
    user_notes: Optional[str] = None
