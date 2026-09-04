"""
API router for Phase 8 Safety & Tool Security Framework endpoints.
Endpoints for audit log inspection, tool permissions, PII scanning, and injection detection checks.
"""

from typing import List, Optional, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.audit_log import AuditLog
from app.schemas.safety import (
    AuditLogEntry,
    PIIRedactionRequest,
    PIIRedactionResponse,
    PromptInjectionCheckRequest,
    PromptInjectionCheckResult,
    ToolPermissionScope,
)
from app.services.security_service import SecurityService, DEFAULT_ROLE_PERMISSIONS

router = APIRouter(prefix="/safety", tags=["safety"])


@router.get("/audit-logs", response_model=List[AuditLogEntry])
def get_audit_logs(
    run_id: Optional[str] = None,
    action_type: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Retrieve immutable security audit logs."""
    query = db.query(AuditLog)
    if run_id:
        query = query.filter(AuditLog.run_id == run_id)
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
    if severity:
        query = query.filter(AuditLog.severity == severity)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [log.to_dict() for log in logs]


@router.get("/permissions", response_model=Dict[str, Any])
def get_tool_permissions(agent_role: Optional[str] = None):
    """Retrieve active role-based tool capability permission matrix."""
    if agent_role:
        role_perm = DEFAULT_ROLE_PERMISSIONS.get(agent_role)
        if not role_perm:
            raise HTTPException(status_code=404, detail=f"Agent role '{agent_role}' not found.")
        return {agent_role: role_perm}
    return DEFAULT_ROLE_PERMISSIONS


@router.post("/scan-pii", response_model=PIIRedactionResponse)
def scan_and_redact_pii(request: PIIRedactionRequest):
    """Scan and redact sensitive PII (emails, tokens, passwords, SSNs) from input text."""
    sanitized, count, detected_types = SecurityService.scan_and_redact_pii(request.text)
    return PIIRedactionResponse(
        original_length=len(request.text),
        sanitized_text=sanitized,
        redactions_count=count,
        detected_types=detected_types,
    )


@router.post("/check-injection", response_model=PromptInjectionCheckResult)
def check_prompt_injection(request: PromptInjectionCheckRequest):
    """Check content for indirect prompt injections, jailbreaks, and payloads."""
    sanitized, is_injection, risk_score, flagged = SecurityService.sanitize_untrusted_content(request.content, source_type=request.source_type)
    return PromptInjectionCheckResult(
        is_injection_detected=is_injection,
        risk_score=risk_score,
        flagged_patterns=flagged,
        sanitized_content=sanitized,
    )
