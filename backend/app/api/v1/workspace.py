"""
REST API endpoints for Multi-Tenant Workspaces, RBAC Roles, and Project Sharing (Phase 13).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as APIQuery
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.rbac_auth import (
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceMemberAdd,
    WorkspaceMemberUpdate,
    WorkspaceMemberResponse,
    ProjectShareRequest,
    ProjectShareResponse,
    OrganizationCreate,
    OrganizationResponse,
)
from app.models.rbac_governance import Workspace, WorkspaceMember, Organization, ProjectShare, User
from app.services.rbac_service import RBACService

router = APIRouter(prefix="/workspaces", tags=["Multi-Tenant Workspaces & RBAC"])


@router.post("/orgs", response_model=OrganizationResponse, status_code=201)
def create_organization(payload: OrganizationCreate, db: Session = Depends(get_db)):
    """Create a new multi-tenant organization."""
    org = Organization(name=payload.name, domain=payload.domain, sso_enabled=payload.sso_enabled, sso_config=payload.sso_config)
    db.add(org)
    db.commit()
    db.refresh(org)
    return org.to_dict()


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(payload: WorkspaceCreate, db: Session = Depends(get_db)):
    """Create a new project team workspace."""
    workspace = Workspace(
        org_id=payload.org_id,
        name=payload.name,
        slug=payload.slug,
        owner_user_id=payload.owner_user_id,
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Assign creator as OWNER
    member = WorkspaceMember(workspace_id=workspace.id, user_id=payload.owner_user_id, role="OWNER")
    db.add(member)
    db.commit()

    return workspace.to_dict()


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(org_id: Optional[str] = APIQuery(None), db: Session = Depends(get_db)):
    """List workspaces in an organization."""
    query = db.query(Workspace)
    if org_id:
        query = query.filter(Workspace.org_id == org_id)
    return [w.to_dict() for w in query.all()]


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
def list_workspace_members(workspace_id: str, db: Session = Depends(get_db)):
    """List members and assigned RBAC roles in a workspace."""
    members = db.query(WorkspaceMember).filter(WorkspaceMember.workspace_id == workspace_id).all()
    return [m.to_dict() for m in members]


@router.post("/{workspace_id}/members", response_model=WorkspaceMemberResponse, status_code=201)
def add_workspace_member(
    workspace_id: str,
    payload: WorkspaceMemberAdd,
    actor_user_id: str = APIQuery("admin_user_id"),
    db: Session = Depends(get_db)
):
    """Assign or invite a user to a workspace with specified RBAC role (OWNER, ADMIN, RESEARCHER, VIEWER)."""
    try:
        member = RBACService.assign_workspace_role(
            db=db,
            workspace_id=workspace_id,
            user_id=payload.user_id,
            role=payload.role,
            actor_user_id=actor_user_id,
        )
        return member.to_dict()
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.post("/projects/{project_id}/share", response_model=ProjectShareResponse)
def share_project_with_workspace(
    project_id: str,
    payload: ProjectShareRequest,
    actor_user_id: str = APIQuery("owner_user_id"),
    db: Session = Depends(get_db)
):
    """Share a research project with a workspace."""
    share = ProjectShare(
        project_id=project_id,
        workspace_id=payload.workspace_id,
        granted_by_user_id=actor_user_id,
        permission_level=payload.permission_level.upper(),
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return share.to_dict()
