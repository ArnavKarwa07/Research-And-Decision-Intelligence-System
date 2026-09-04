"""
Unit tests for Phase 8 Human-in-the-Loop (HITL) Service & Gatekeeper Agent.
Tests approval gates, 5-minute auto-kill timeout, clarification questions, evidence override, and assumption updates.
"""

import pytest
from datetime import datetime, timezone, timedelta

# Import app.models first so all SQLAlchemy models are registered on Base
import app.models
from app.models.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.approval_gate import ApprovalGate, ApprovalGateStatus
from app.models.clarification import ClarificationQuestion, ClarificationStatus
from app.models.claim import Claim
from app.models.query import Query
from app.models.hypothesis import Hypothesis
from app.models.session import Session as UserSession
from sqlalchemy.pool import StaticPool
from app.services.hitl_service import HITLService

# Setup sqlite in-memory test database
engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def test_create_and_resolve_approval_gate(db):
    gate = HITLService.create_approval_gate(
        db=db,
        run_id="run-123",
        agent_id="data_agent",
        tool_name="python_sandbox",
        description="Execute python script for statistical regression.",
    )

    assert gate.id is not None
    assert gate.status == ApprovalGateStatus.PENDING.value

    # Resolve approval gate
    resolved = HITLService.resolve_approval_gate(db=db, gate_id=gate.id, action="approve", user_feedback="Looks safe")
    assert resolved.status == ApprovalGateStatus.APPROVED.value
    assert resolved.user_feedback == "Looks safe"


def test_approval_gate_auto_kill_timeout(db):
    gate = HITLService.create_approval_gate(
        db=db,
        run_id="run-456",
        agent_id="data_agent",
        tool_name="execute_sql_query",
        timeout_seconds=300,  # 5-minute auto-kill
    )

    # Manually backdate created_at by 6 minutes (360s) to simulate 5-minute timeout expiry
    gate.created_at = datetime.now(timezone.utc) - timedelta(seconds=360)
    db.commit()

    # Trigger auto-kill timeout check
    killed_count = HITLService.check_and_apply_timeouts(db, run_id="run-456")
    assert killed_count == 1

    db.refresh(gate)
    assert gate.status == ApprovalGateStatus.EXPIRED.value
    assert "5-minute timeout" in gate.user_feedback


def test_clarification_question_lifecycle(db):
    clar = HITLService.create_clarification_question(
        db=db,
        run_id="run-789",
        agent_id="gatekeeper_agent",
        prompt="Which metric should be prioritized?",
        options=["Revenue", "EBITDA", "User Growth"],
    )

    assert clar.status == ClarificationStatus.PENDING.value

    answered = HITLService.answer_clarification_question(db=db, clarification_id=clar.id, answer="Revenue")
    assert answered.status == ClarificationStatus.ANSWERED.value
    assert answered.answer == "Revenue"


def test_claim_evidence_override(db):
    s = UserSession()
    db.add(s)
    db.commit()

    q = Query(session_id=s.id, text="Test query")
    db.add(q)
    db.commit()

    c = Claim(query_id=q.id, content="Sample claim content", claim_type="FACT", status="unverified")
    db.add(c)
    db.commit()

    updated = HITLService.override_claim_evidence(db=db, claim_id=str(c.id), new_status="supported", notes="User verified manually")
    assert updated.status == "supported"
    assert updated.metadata_["user_notes"] == "User verified manually"


def test_hypothesis_assumption_confirmation(db):
    s = UserSession()
    db.add(s)
    db.commit()

    q = Query(session_id=s.id, text="Hypothesis test query")
    db.add(q)
    db.commit()

    h = Hypothesis(query_id=q.id, statement="Preliminary assumption about market expansion", status="proposed")
    db.add(h)
    db.commit()

    confirmed_h = HITLService.confirm_hypothesis_assumption(db=db, hypothesis_id=str(h.id), confirmed=True, user_notes="Confirmed by domain expert")
    assert confirmed_h.status == "confirmed"

    rejected_h = HITLService.confirm_hypothesis_assumption(db=db, hypothesis_id=str(h.id), confirmed=False, user_notes="Invalid assumption")
    assert rejected_h.status == "rejected"


@pytest.mark.asyncio
async def test_gatekeeper_agent_step():
    from app.agents.gatekeeper_agent import GatekeeperAgent

    agent = GatekeeperAgent()

    # 1. Ambiguous query test
    res1 = await agent.step({"query_text": "do whatever choose for me", "agent_role": "research"})
    assert res1.result["needs_clarification"] is True
    assert len(res1.result["suggested_options"]) > 0

    # 2. High-risk tool call test
    res2 = await agent.step({"query_text": "Analyze financial dataset with regression", "tool_name": "python_sandbox", "agent_role": "data_agent"})
    assert res2.result["requires_approval_gate"] is True
    assert res2.result["risk_level"] == "high"
    assert res2.result["timeout_seconds"] == 300
