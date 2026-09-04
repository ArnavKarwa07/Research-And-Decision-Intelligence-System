"""
GovernanceAgent implementation (Phase 13 Collaboration & Governance Engine).
Specialized subagent executing RBAC permission audits, workspace security checks, and immutable compliance audit reports.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.agents.agent_contracts import GovernanceAgentInput, GovernanceAgentOutput
from app.services.enterprise_audit_service import EnterpriseAuditService
from app.models.rbac_governance import WorkspaceMember, AuthTokenSession

logger = logging.getLogger(__name__)


class GovernanceAgent:
    """Specialized Agent for Governance, RBAC Permission Audits & Security Controls."""

    def __init__(self, db: Session):
        self.db = db

    def execute(self, agent_input: GovernanceAgentInput) -> GovernanceAgentOutput:
        """Run GovernanceAgent compliance report and permission audit."""
        logger.info(f"[GOVERNANCE_AGENT] Running audit for org {agent_input.org_id} (scope={agent_input.audit_scope})")

        report_id = str(uuid.uuid4())
        logs = EnterpriseAuditService.query_audit_logs(
            db=self.db,
            org_id=agent_input.org_id,
            workspace_id=agent_input.workspace_id,
            limit=200,
        )

        violations = []
        unauthorized_count = 0

        for log in logs:
            if log.severity in ("WARNING", "ERROR", "CRITICAL") or "DENIED" in log.action_type:
                unauthorized_count += 1
                violations.append({
                    "log_id": log.id,
                    "action_type": log.action_type,
                    "severity": log.severity,
                    "user_id": log.user_id,
                    "details": log.details,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                })

        # Calculate compliance score
        total_events = len(logs)
        compliance_score = max(0.0, 1.0 - (len(violations) * 0.05)) if total_events > 0 else 1.0

        recommendations = [
            "Maintain strict RBAC permission checks across all project sharing actions.",
            "Verify session token revocation lists are synchronized with Redis.",
            "Schedule quarterly governance audits for all enterprise connectors.",
        ]
        if violations:
            recommendations.insert(0, f"Review {len(violations)} flagged security events and unauthorized permission attempts.")

        return GovernanceAgentOutput(
            audit_report_id=report_id,
            org_id=agent_input.org_id,
            workspace_id=agent_input.workspace_id,
            total_events_scanned=total_events,
            security_violations_detected=violations,
            unauthorized_attempts_count=unauthorized_count,
            compliance_score=round(compliance_score, 2),
            recommendations=recommendations,
            stop_reason="OBJECTIVE_SATISFIED",
            summary_message=(
                f"Governance audit report '{report_id}' generated with compliance score {round(compliance_score, 2) * 100}%. "
                f"Scanned {total_events} events, flagged {len(violations)} security violations."
            ),
        )
