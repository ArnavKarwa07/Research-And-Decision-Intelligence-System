"""
Safety & Security Specialist Agent (Phase 8).
Responsible for verifying tool permissions, scanning inputs/outputs for PII, sanitizing untrusted content for indirect prompt injections, and generating security audit events.
"""

import logging
from typing import Dict, Any
from app.agents.base import BaseAgent, AgentConfig, StepResult
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)


class SafetyAgent(BaseAgent):
    def __init__(self, config: AgentConfig = None):
        if not config:
            config = AgentConfig(
                max_steps=10,
                max_tokens=10000,
                timeout_seconds=30,
                allowed_tools=["scan_pii", "sanitize_injection", "check_permission"],
            )
        super().__init__(config, agent_type="safety_agent")
        self.last_result: Dict[str, Any] = {}

    async def step(self, input_data: Dict[str, Any]) -> StepResult:
        content = input_data.get("content", "")
        agent_role = input_data.get("agent_role", "research")
        tool_name = input_data.get("tool_name", None)

        # 1. Tool Permission Check if tool_name is provided
        perm_allowed, req_approval, perm_reason = True, False, ""
        if tool_name:
            perm_allowed, req_approval, perm_reason = SecurityService.check_tool_permission(agent_role, tool_name)

        # 2. PII Scan
        clean_content, redaction_count, detected_pii = SecurityService.scan_and_redact_pii(content)

        # 3. Prompt Injection Defense
        sanitized_content, is_injection, risk_score, flagged_patterns = SecurityService.sanitize_untrusted_content(
            clean_content if isinstance(clean_content, str) else str(clean_content)
        )

        # 4. Optional Security Audit Logging if db session and action_type provided
        db = input_data.get("db")
        action_type = input_data.get("action_type")
        if db and action_type:
            SecurityService.log_audit_event(
                db=db,
                action_type=action_type,
                severity=input_data.get("severity", "INFO"),
                run_id=input_data.get("run_id"),
                agent_id=input_data.get("agent_id", "safety_agent"),
                details={
                    "agent_role": agent_role,
                    "tool_name": tool_name,
                    "permission_allowed": perm_allowed,
                    "requires_approval": req_approval,
                    "pii_redaction_count": redaction_count,
                    "is_injection_detected": is_injection,
                    "risk_score": risk_score,
                },
            )

        self.last_result = {
            "permission_allowed": perm_allowed,
            "requires_approval": req_approval,
            "permission_reason": perm_reason,
            "redacted_content": clean_content,
            "pii_redaction_count": redaction_count,
            "detected_pii_types": detected_pii,
            "sanitized_content": sanitized_content,
            "is_injection_detected": is_injection,
            "risk_score": risk_score,
            "flagged_patterns": flagged_patterns,
        }

        return StepResult(
            action="safety_scan_complete",
            result=self.last_result,
            tokens_used=100,
            should_continue=False,
            message=f"Safety scan complete. Injection detected: {is_injection}, PII redacted: {redaction_count}",
        )

    async def compile_output(self) -> Dict[str, Any]:
        return self.last_result
