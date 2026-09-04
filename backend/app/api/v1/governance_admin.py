"""
REST API endpoints for Enterprise Governance Controls, Audit Logs & Governance Agent (Phase 13).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as APIQuery
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.rbac_auth import EnterpriseAuditLogResponse, AuditLogQueryFilter
from app.services.enterprise_audit_service import EnterpriseAuditService
from app.agents.governance_agent import GovernanceAgent
from app.agents.agent_contracts import GovernanceAgentInput, GovernanceAgentOutput

router = APIRouter(prefix="/governance", tags=["Admin Governance & Audit Logs"])


@router.get("/audit-logs", response_model=List[EnterpriseAuditLogResponse])
def search_audit_logs(
    org_id: Optional[str] = APIQuery(None),
    workspace_id: Optional[str] = APIQuery(None),
    user_id: Optional[str] = APIQuery(None),
    category: Optional[str] = APIQuery(None),
    severity: Optional[str] = APIQuery(None),
    limit: int = APIQuery(50, le=500),
    db: Session = Depends(get_db)
):
    """Query immutable enterprise audit logs filtered by organization, workspace, category, or severity."""
    logs = EnterpriseAuditService.query_audit_logs(
        db=db,
        org_id=org_id,
        workspace_id=workspace_id,
        user_id=user_id,
        category=category,
        severity=severity,
        limit=limit,
    )
    return [l.to_dict() for l in logs]


@router.post("/audit-reports", response_model=GovernanceAgentOutput)
def generate_governance_report(
    org_id: str = APIQuery("default-org"),
    workspace_id: Optional[str] = APIQuery(None),
    audit_scope: str = APIQuery("FULL_COMPLIANCE_REPORT"),
    db: Session = Depends(get_db)
):
    """Execute GovernanceAgent to generate comprehensive RBAC compliance and audit report."""
    try:
        agent = GovernanceAgent(db=db)
        agent_input = GovernanceAgentInput(
            org_id=org_id,
            workspace_id=workspace_id,
            audit_scope=audit_scope,
        )
        return agent.execute(agent_input)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Governance audit failed: {e}")
