"""
SQLAlchemy models for RBAC, Workspaces, SSO Authentication, and Enterprise Audit Logs (Phase 13).
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, Boolean, ForeignKey, Integer
from app.models.base import Base, TimestampMixin


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=True, unique=True, index=True)
    sso_enabled = Column(Boolean, nullable=False, default=False)
    sso_config = Column(JSON, nullable=True)  # Provider metadata, OAuth/SAML client IDs, issuer URLs

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain,
            "sso_enabled": self.sso_enabled,
            "sso_config": self.sso_config or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), nullable=False, index=True)
    owner_user_id = Column(String(36), nullable=False, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "org_id": self.org_id,
            "name": self.name,
            "slug": self.slug,
            "owner_user_id": self.owner_user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=False, unique=True, index=True)
    full_name = Column(String(255), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_superadmin = Column(Boolean, nullable=False, default=False)
    sso_provider = Column(String(50), nullable=True)  # google, azure_ad, okta, saml, mock
    sso_subject_id = Column(String(255), nullable=True, index=True)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "org_id": self.org_id,
            "email": self.email,
            "full_name": self.full_name,
            "is_active": self.is_active,
            "is_superadmin": self.is_superadmin,
            "sso_provider": self.sso_provider,
            "sso_subject_id": self.sso_subject_id,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="RESEARCHER", index=True)  # OWNER, ADMIN, RESEARCHER, VIEWER
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "role": self.role,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
        }


class ProjectShare(Base):
    __tablename__ = "project_shares"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, index=True)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by_user_id = Column(String(36), nullable=False)
    permission_level = Column(String(50), nullable=False, default="READ")  # READ, WRITE, ADMIN
    shared_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "workspace_id": self.workspace_id,
            "granted_by_user_id": self.granted_by_user_id,
            "permission_level": self.permission_level,
            "shared_at": self.shared_at.isoformat() if self.shared_at else None,
        }


class AuthTokenSession(Base):
    __tablename__ = "auth_token_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(100), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    is_revoked = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "token_hash": self.token_hash[:10] + "...",
            "device_info": self.device_info,
            "ip_address": self.ip_address,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_revoked": self.is_revoked,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EnterpriseAuditLog(Base):
    __tablename__ = "enterprise_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String(36), nullable=True, index=True)
    workspace_id = Column(String(36), nullable=True, index=True)
    user_id = Column(String(36), nullable=True, index=True)
    agent_id = Column(String(100), nullable=True, index=True)
    action_type = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, default="DATA_ACCESS", index=True)  # DATA_ACCESS, CONNECTOR_SYNC, ROLE_CHANGE, SSO_LOGIN, ADMIN_OVERRIDE, SECURITY_BREACH
    severity = Column(String(20), nullable=False, default="INFO", index=True)  # INFO, WARNING, ERROR, CRITICAL
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "org_id": self.org_id,
            "workspace_id": self.workspace_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "action_type": self.action_type,
            "category": self.category,
            "severity": self.severity,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details or {},
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
