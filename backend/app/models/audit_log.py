"""
SQLAlchemy model for Security Audit Logs (Phase 8 Tool Security Framework).
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), nullable=True, index=True)
    agent_id = Column(String(100), nullable=True, index=True)
    action_type = Column(String(100), nullable=False, index=True)  # tool_invocation, approval_requested, prompt_injection_detected, etc.
    severity = Column(String(20), nullable=False, default="INFO", index=True)  # INFO, WARNING, ERROR, CRITICAL
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "severity": self.severity,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
