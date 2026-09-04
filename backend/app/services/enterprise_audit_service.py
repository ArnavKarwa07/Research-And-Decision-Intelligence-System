"""
Enterprise Audit Logging & Compliance Query Engine (Phase 13).
Provides immutable audit trail recording and filtering for organizational data access, connector syncs, RBAC role changes, SSO events, and admin governance overrides.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.rbac_governance import EnterpriseAuditLog
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class EnterpriseAuditService:
    """Service writing and querying immutable enterprise audit logs."""

    @staticmethod
    def record_event(
        db: Session,
        action_type: str,
        category: str = "DATA_ACCESS",  # DATA_ACCESS, CONNECTOR_SYNC, ROLE_CHANGE, SSO_LOGIN, ADMIN_OVERRIDE, SECURITY_BREACH
        severity: str = "INFO",  # INFO, WARNING, ERROR, CRITICAL
        org_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> EnterpriseAuditLog:
        """Write an immutable audit log entry to database."""
        # Scan and redact PII from audit details before storing
        clean_details, _, _ = SecurityService.scan_and_redact_pii(details or {})

        audit_entry = EnterpriseAuditLog(
            org_id=org_id,
            workspace_id=workspace_id,
            user_id=user_id,
            agent_id=agent_id,
            action_type=action_type,
            category=category.upper(),
            severity=severity.upper(),
            resource_type=resource_type,
            resource_id=resource_id,
            details=clean_details,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)

        logger.info(f"[ENTERPRISE_AUDIT] [{severity}] {action_type} | Category: {category} | User: {user_id} | Workspace: {workspace_id}")
        return audit_entry

    @staticmethod
    def query_audit_logs(
        db: Session,
        org_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
    ) -> List[EnterpriseAuditLog]:
        """Query immutable audit logs filtered by organization, workspace, user, category, or severity."""
        query = db.query(EnterpriseAuditLog)

        if org_id:
            query = query.filter(EnterpriseAuditLog.org_id == org_id)
        if workspace_id:
            query = query.filter(EnterpriseAuditLog.workspace_id == workspace_id)
        if user_id:
            query = query.filter(EnterpriseAuditLog.user_id == user_id)
        if category:
            query = query.filter(EnterpriseAuditLog.category == category.upper())
        if severity:
            query = query.filter(EnterpriseAuditLog.severity == severity.upper())

        query = query.order_by(desc(EnterpriseAuditLog.timestamp)).limit(limit)
        return query.all()
