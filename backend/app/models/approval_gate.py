"""
SQLAlchemy model for Approval Gates (Phase 8 Human-in-the-Loop).
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, Enum as SQLEnum
import enum
from app.models.base import Base


class ApprovalGateStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"  # 5-minute auto-kill timeout


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalGate(Base):
    __tablename__ = "approval_gates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False)
    tool_name = Column(String(100), nullable=False)
    tool_args = Column(JSON, nullable=True)
    risk_level = Column(String(20), nullable=False, default=RiskLevel.HIGH.value)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default=ApprovalGateStatus.PENDING.value, index=True)
    user_feedback = Column(Text, nullable=True)
    timeout_seconds = Column(Integer, nullable=False, default=300)  # 5-minute default auto-kill
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "risk_level": self.risk_level,
            "description": self.description,
            "status": self.status,
            "user_feedback": self.user_feedback,
            "timeout_seconds": self.timeout_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
