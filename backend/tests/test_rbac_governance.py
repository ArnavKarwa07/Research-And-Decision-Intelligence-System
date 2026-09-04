"""
Automated unit & integration tests for RBAC & Multi-Tenant Permission Governance (Phase 13).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.rbac_governance import Organization, Workspace, User, WorkspaceMember, ProjectShare
from app.services.rbac_service import RBACService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()

    org = Organization(name="Test Org", domain="test.com")
    db.add(org)
    db.commit()

    user_owner = User(org_id=org.id, email="owner@test.com", full_name="Owner User")
    user_admin = User(org_id=org.id, email="admin@test.com", full_name="Admin User")
    user_researcher = User(org_id=org.id, email="researcher@test.com", full_name="Researcher User")
    user_viewer = User(org_id=org.id, email="viewer@test.com", full_name="Viewer User")
    db.add_all([user_owner, user_admin, user_researcher, user_viewer])
    db.commit()

    workspace = Workspace(org_id=org.id, name="Test WS", slug="test-ws", owner_user_id=user_owner.id)
    db.add(workspace)
    db.commit()

    m_owner = WorkspaceMember(workspace_id=workspace.id, user_id=user_owner.id, role="OWNER")
    m_admin = WorkspaceMember(workspace_id=workspace.id, user_id=user_admin.id, role="ADMIN")
    m_researcher = WorkspaceMember(workspace_id=workspace.id, user_id=user_researcher.id, role="RESEARCHER")
    m_viewer = WorkspaceMember(workspace_id=workspace.id, user_id=user_viewer.id, role="VIEWER")
    db.add_all([m_owner, m_admin, m_researcher, m_viewer])
    db.commit()

    yield db, workspace.id, user_owner.id, user_admin.id, user_researcher.id, user_viewer.id
    db.close()


def test_rbac_permission_matrix(test_db):
    db, ws_id, owner_id, admin_id, researcher_id, viewer_id = test_db

    # OWNER permissions
    assert RBACService.has_permission(db, owner_id, ws_id, "workspace:manage") is True
    assert RBACService.has_permission(db, owner_id, ws_id, "admin:override") is True

    # ADMIN permissions
    assert RBACService.has_permission(db, admin_id, ws_id, "connector:manage") is True
    assert RBACService.has_permission(db, admin_id, ws_id, "admin:override") is False

    # RESEARCHER permissions
    assert RBACService.has_permission(db, researcher_id, ws_id, "task:execute") is True
    assert RBACService.has_permission(db, researcher_id, ws_id, "connector:manage") is False

    # VIEWER permissions
    assert RBACService.has_permission(db, viewer_id, ws_id, "project:read") is True
    assert RBACService.has_permission(db, viewer_id, ws_id, "project:write") is False


def test_assign_workspace_role(test_db):
    db, ws_id, owner_id, admin_id, researcher_id, viewer_id = test_db

    # Owner promotes Viewer to ADMIN
    member = RBACService.assign_workspace_role(db, ws_id, viewer_id, "ADMIN", actor_user_id=owner_id)
    assert member.role == "ADMIN"
    assert RBACService.has_permission(db, viewer_id, ws_id, "connector:manage") is True

    # Non-admin attempting role modification fails
    with pytest.raises(PermissionError):
        RBACService.assign_workspace_role(db, ws_id, researcher_id, "OWNER", actor_user_id=researcher_id)
