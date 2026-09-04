"""
Automated unit & integration tests for SSO Authentication & Session Revocation (Phase 13).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.sso_auth_service import SSOAuthService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_initiate_sso_flow():
    res = SSOAuthService.initiate_sso_flow("google")
    assert res["provider"] == "google"
    assert "accounts.google.com" in res["auth_url"]
    assert len(res["state"]) > 10


def test_sso_callback_and_session_issuance(test_db):
    user, session, access_token, refresh_token = SSOAuthService.authenticate_sso_callback(
        db=test_db,
        provider="google",
        code="mock_code_123",
    )

    assert user.email is not None
    assert session.is_revoked is False
    assert len(access_token) > 10
    assert len(refresh_token) > 10

    # Token check
    assert SSOAuthService.is_token_revoked(test_db, access_token) is False

    # Revoke session
    revoked = SSOAuthService.revoke_session(test_db, session.id, actor_user_id=user.id)
    assert revoked is True

    # Token check after revocation
    assert SSOAuthService.is_token_revoked(test_db, access_token) is True
