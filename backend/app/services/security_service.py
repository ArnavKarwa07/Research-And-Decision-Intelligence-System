"""
Security & Safety Service (Phase 8 Tool Security Framework).
Handles tool permission scoping, PII detection & redaction, indirect prompt injection defense, and security audit logging.
"""

import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# Default role-based tool permissions matrix
DEFAULT_ROLE_PERMISSIONS = {
    "research": {
        "allowed": ["web_search", "content_extractor", "summarize"],
        "denied": ["python_sandbox", "execute_sql_query"],
        "requires_approval": [],
    },
    "data_agent": {
        "allowed": ["sql_schema_inspect", "csv_inspect", "chart_generate"],
        "denied": ["web_search"],
        "requires_approval": ["python_sandbox", "execute_sql_query"],
    },
    "supervisor": {
        "allowed": ["web_search", "content_extractor", "summarize", "sql_schema_inspect", "csv_inspect", "chart_generate"],
        "denied": [],
        "requires_approval": ["python_sandbox", "execute_sql_query"],
    },
}

# Regex patterns for PII detection
# Regex patterns for PII detection
PII_PATTERNS = {
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "SSN": r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
    "API_TOKEN": r"\b(?:sk|pk|api|token|secret)(?:_[a-zA-Z0-9]+)*[_-][a-zA-Z0-9_-]{12,64}\b",
    "BEARER_TOKEN": r"\bBearer\s+[A-Za-z0-9\-\._~\+\/]+=*\b",
    "PASSWORD_PARAM": r"(?i)(?:password|passwd|secret|access_key)\s*[:=]\s*['\"]?([^'\"\s]+)['\"]?",
}

# Heuristics & patterns for Indirect Prompt Injection / Jailbreak Attacks / ROM injections
INJECTION_PATTERNS = [
    r"ignore\s+all\s+previous\s+instructions",
    r"disregard\s+prior\s+directives",
    r"system\s*prompt\s*override",
    r"you\s+are\s+now\s+in\s+DAN\s+mode",
    r"bypass\s+safety\s+filter",
    r"execute\s+arbitrary\s+code",
    r"<script\b[^>]*>",
    r"drop\s+table\s+",
    r"delete\s+from\s+",
    r"eval\(",
    r"exec\(",
    r"__import__",
    r"process\.env",
]


class SecurityService:
    @staticmethod
    def check_tool_permission(agent_role: str, tool_name: str) -> Tuple[bool, bool, str]:
        """
        Check if an agent role is authorized to execute a tool.
        Returns: (is_allowed, requires_approval, reason)
        """
        role_config = DEFAULT_ROLE_PERMISSIONS.get(agent_role)
        if not role_config:
            # Fallback for unknown role: deny execution for security safety
            return False, False, f"Agent role '{agent_role}' is not recognized."

        if tool_name in role_config.get("denied", []):
            return False, False, f"Tool '{tool_name}' is explicitly denied for agent role '{agent_role}'."

        if tool_name in role_config.get("requires_approval", []):
            return True, True, f"Tool '{tool_name}' requires human approval for agent role '{agent_role}'."

        if tool_name in role_config.get("allowed", []):
            return True, False, f"Tool '{tool_name}' is permitted for agent role '{agent_role}'."

        # Default fallback: allow but require approval for unknown tools under recognized role
        return True, True, f"Unclassified tool '{tool_name}' requires approval."

    @staticmethod
    def scan_and_redact_pii(data: Any) -> Tuple[Any, int, List[str]]:
        """
        Scan string, dict, or list for sensitive PII and redact matching patterns.
        Returns: (redacted_data, total_redactions_count, detected_types)
        """
        if isinstance(data, str):
            text = data
            detected_types = set()
            count = 0

            for pii_type, pattern in PII_PATTERNS.items():
                matches = re.findall(pattern, text)
                if matches:
                    count += len(matches)
                    detected_types.add(pii_type)
                    text = re.sub(pattern, lambda m: f"[REDACTED_{pii_type}]", text)

            return text, count, list(detected_types)

        elif isinstance(data, dict):
            new_dict = {}
            total_count = 0
            all_types = set()
            for k, v in data.items():
                # Redact keys containing secret or password
                if any(sec in k.lower() for sec in ["password", "passwd", "secret", "token", "api_key", "apikey", "ssn", "credentials", "access_key"]):
                    new_dict[k] = "[REDACTED_SECRET]"
                    total_count += 1
                    all_types.add("SECRET_KEY")
                else:
                    redacted_v, c, t = SecurityService.scan_and_redact_pii(v)
                    new_dict[k] = redacted_v
                    total_count += c
                    all_types.update(t)

            return new_dict, total_count, list(all_types)

        elif isinstance(data, list):
            new_list = []
            total_count = 0
            all_types = set()
            for item in data:
                redacted_i, c, t = SecurityService.scan_and_redact_pii(item)
                new_list.append(redacted_i)
                total_count += c
                all_types.update(t)
            return new_list, total_count, list(all_types)

        return data, 0, []

    @staticmethod
    def sanitize_untrusted_content(content: str, source_type: str = "web") -> Tuple[str, bool, float, List[str]]:
        """
        Scan untrusted retrieved content for indirect prompt injections, jailbreaks, and payloads.
        Wraps content in isolated XML tags and flags threats.
        Returns: (sanitized_content, is_injection_detected, risk_score, flagged_patterns)
        """
        if not isinstance(content, str):
            return str(content), False, 0.0, []

        flagged = []
        for pattern in INJECTION_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                flagged.append(pattern)

        is_injection = len(flagged) > 0
        risk_score = min(1.0, len(flagged) * 0.35)

        # Neutralize dangerous prompt override commands in untrusted content
        clean_content = content
        for pattern in flagged:
            clean_content = re.sub(pattern, lambda m: f"[BLOCKED_INJECTION_PATTERN: {m.group(0)}]", clean_content, flags=re.IGNORECASE)

        # Structural containment wrapping
        sanitized_content = (
            f"<untrusted_content source='{source_type}' injection_flagged='{is_injection}'>\n"
            f"{clean_content}\n"
            f"</untrusted_content>"
        )

        return sanitized_content, is_injection, risk_score, flagged

    @staticmethod
    def log_audit_event(
        db: Session,
        action_type: str,
        severity: str = "INFO",
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        """
        Write an immutable security audit event to the database.
        """
        # Ensure any PII inside details is redacted before persisting to audit log
        sanitized_details, _, _ = SecurityService.scan_and_redact_pii(details or {})

        audit_entry = AuditLog(
            run_id=run_id,
            agent_id=agent_id,
            action_type=action_type,
            severity=severity,
            details=sanitized_details,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(audit_entry)
        db.commit()
        db.refresh(audit_entry)

        logger.info(f"[AUDIT_LOG] [{severity}] Action: {action_type} | Agent: {agent_id} | Run: {run_id}")
        return audit_entry
