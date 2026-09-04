"""
SQLAlchemy model for Clarification Questions (Phase 8 Human-in-the-Loop).
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, Enum as SQLEnum
import enum
from app.models.base import Base


class ClarificationStatus(str, enum.Enum):
    PENDING = "pending"
    ANSWERED = "answered"
    EXPIRED = "expired"  # 5-minute auto-kill timeout


class ClarificationQuestion(Base):
    __tablename__ = "clarification_questions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), nullable=False, index=True)
    agent_id = Column(String(100), nullable=False)
    prompt = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # List of suggested response choices
    answer = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default=ClarificationStatus.PENDING.value, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at = Column(DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "prompt": self.prompt,
            "options": self.options,
            "answer": self.answer,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }
