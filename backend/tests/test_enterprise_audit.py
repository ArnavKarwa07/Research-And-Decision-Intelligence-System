"""
Automated unit & integration tests for Enterprise Audit Logging (Phase 13).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.enterprise_audit_service import EnterpriseAuditService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_record_and_query_audit_events(test_db):
    log1 = EnterpriseAuditService.record_event(
        db=test_db,
        action_type="SSO_LOGIN_SUCCESS",
        category="SSO_LOGIN",
        severity="INFO",
        org_id="org_1",
        workspace_id="ws_1",
        user_id="user_1",
        details={"provider": "google", "password": "supersecretpassword"},  # PII test
    )

    assert log1.id is not None
    # PII in details should be redacted
    assert log1.details.get("password") == "[REDACTED_SECRET]"

    logs = EnterpriseAuditService.query_audit_logs(test_db, workspace_id="ws_1")
    assert len(logs) == 1
    assert logs[0].action_type == "SSO_LOGIN_SUCCESS"
