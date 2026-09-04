"""
Pydantic schemas for RBAC, Workspaces, SSO Authentication, and Enterprise Audit Logs (Phase 13).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


class OrganizationCreate(BaseModel):
    name: str = Field(..., description="Organization name")
    domain: Optional[str] = Field(default=None, description="Primary domain e.g. company.com")
    sso_enabled: bool = Field(default=False)
    sso_config: Optional[Dict[str, Any]] = None


class OrganizationResponse(BaseModel):
    id: str
    name: str
    domain: Optional[str] = None
    sso_enabled: bool
    sso_config: Dict[str, Any]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WorkspaceCreate(BaseModel):
    org_id: str
    name: str
    slug: str
    owner_user_id: str


class WorkspaceResponse(BaseModel):
    id: str
    org_id: str
    name: str
    slug: str
    owner_user_id: str
    created_at: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    org_id: Optional[str] = None
    email: str
    full_name: str
    is_active: bool
    is_superadmin: bool
    sso_provider: Optional[str] = None
    last_login_at: Optional[str] = None
    created_at: Optional[str] = None


class WorkspaceMemberAdd(BaseModel):
    user_id: str
    role: str = Field(default="RESEARCHER", description="OWNER, ADMIN, RESEARCHER, VIEWER")


class WorkspaceMemberUpdate(BaseModel):
    role: str = Field(..., description="OWNER, ADMIN, RESEARCHER, VIEWER")


class WorkspaceMemberResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: str
    joined_at: str


class ProjectShareRequest(BaseModel):
    workspace_id: str
    permission_level: str = Field(default="READ", description="READ, WRITE, ADMIN")


class ProjectShareResponse(BaseModel):
    id: str
    project_id: str
    workspace_id: str
    granted_by_user_id: str
    permission_level: str
    shared_at: str


class SSOLoginRequest(BaseModel):
    provider: str = Field(..., description="google, azure_ad, okta, saml, mock")
    redirect_uri: Optional[str] = None


class SSOCallbackRequest(BaseModel):
    provider: str
    code: str
    state: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserResponse


class TokenRefreshRequest(BaseModel):
    refresh_token: str


class AuditLogQueryFilter(BaseModel):
    org_id: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    category: Optional[str] = None  # DATA_ACCESS, CONNECTOR_SYNC, ROLE_CHANGE, SSO_LOGIN, ADMIN_OVERRIDE, SECURITY_BREACH
    severity: Optional[str] = None  # INFO, WARNING, ERROR, CRITICAL
    limit: int = Field(default=50, le=500)


class EnterpriseAuditLogResponse(BaseModel):
    id: str
    org_id: Optional[str] = None
    workspace_id: Optional[str] = None
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    action_type: str
    category: str
    severity: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any]
    timestamp: str
