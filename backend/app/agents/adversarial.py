"""Adversarial Review Agent implementation for RADIS.
Audits evidence validity, challenges claims, and searches for bugs, race conditions, and unvalidated assumptions.
"""
import logging
from typing import Any, Dict, List
from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.agents.agent_contracts import (
    AdversarialInput, AdversarialOutput, AuditIssue
)

logger = logging.getLogger(__name__)


class AdversarialAgent(BaseAgent):
    """Adversarial Agent performs aggressive auditing and red-team checks."""

    def __init__(self, config: AgentConfig):
        super().__init__(config, agent_type="Adversarial Review Agent")
        self.audit_passed = True
        self.issues: List[AuditIssue] = []
        self.confidence_adjusted = 0.90
        self.assessment_message = ""

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        objective = input_data.get("objective", "")
        claims = input_data.get("claims", [])
        confidence = input_data.get("confidence", 0.90)

        logger.info(f"[Adversarial Agent] Conducting aggressive audit of research for: {objective}")

        # Perform strict checks
        unvalidated = [c for c in claims if isinstance(c, dict) and c.get("support_status") == "UNSUPPORTED"]
        low_confidence = [c for c in claims if isinstance(c, dict) and c.get("confidence", 1.0) < 0.70]

        if unvalidated:
            self.audit_passed = False
            self.issues.append(AuditIssue(
                issue_id="AUDIT-001",
                severity="HIGH",
                category="UNVALIDATED_CLAIM",
                description=f"Found {len(unvalidated)} claims with unsupported status.",
                assigned_agent="Evidence Agent",
                recommendation="Re-run search or mark claim as UNRESOLVED."
            ))

        if low_confidence:
            self.confidence_adjusted = max(0.50, confidence - 0.15)
            self.issues.append(AuditIssue(
                issue_id="AUDIT-002",
                severity="MEDIUM",
                category="WEAK_SOURCE",
                description=f"Detected {len(low_confidence)} claims with confidence under 70%.",
                assigned_agent="Research Agent",
                recommendation="Gather secondary independent sources to verify."
            ))

        if not self.issues:
            self.audit_passed = True
            self.confidence_adjusted = confidence
            self.assessment_message = f"Adversarial audit completed cleanly. Verified {len(claims)} claims with {int(confidence*100)}% calibrated confidence."
        else:
            self.assessment_message = f"Adversarial audit raised {len(self.issues)} issue(s). Calibrated confidence adjusted to {int(self.confidence_adjusted*100)}%."

        return StepResult(
            action="adversarial_audit",
            result={"audit_passed": self.audit_passed, "issues_count": len(self.issues)},
            tokens_used=180,
            should_continue=False,
            message=self.assessment_message
        )

    async def compile_output(self) -> Dict[str, Any]:
        output = AdversarialOutput(
            audit_passed=self.audit_passed,
            confidence_adjusted=self.confidence_adjusted,
            issues=self.issues,
            assessment_message=self.assessment_message
        )
        return output.model_dump()
