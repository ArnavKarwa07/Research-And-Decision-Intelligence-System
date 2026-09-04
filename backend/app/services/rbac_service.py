"""
Role-Based Access Control (RBAC) & Multi-Tenant Permission Service (Phase 13).
Handles 4-tier permission enforcement (OWNER, ADMIN, RESEARCHER, VIEWER), project sharing, and workspace access checks.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.rbac_governance import Workspace, WorkspaceMember, User, ProjectShare
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)

# Permission Matrix Definition
ROLE_PERMISSIONS = {
    "OWNER": {
        "workspace:manage",
        "workspace:delete",
        "member:manage",
        "project:write",
        "project:read",
        "project:share",
        "task:execute",
        "document:ingest",
        "connector:manage",
        "memory:read",
        "memory:write",
        "audit:read",
        "admin:override",
    },
    "ADMIN": {
        "workspace:manage",
        "member:manage",
        "project:write",
        "project:read",
        "project:share",
        "task:execute",
        "document:ingest",
        "connector:manage",
        "memory:read",
        "memory:write",
        "audit:read",
    },
    "RESEARCHER": {
        "project:write",
        "project:read",
        "task:execute",
        "document:ingest",
        "connector:read",
        "memory:read",
        "memory:write",
    },
    "VIEWER": {
        "project:read",
        "memory:read",
        "audit:read",
    },
}


class RBACService:
    """Service checking user permissions, workspace roles, and project shares."""

    @staticmethod
    def get_user_workspace_role(db: Session, user_id: str, workspace_id: str) -> Optional[str]:
        """Fetch a user's role in a given workspace."""
        # Superadmins bypass to OWNER
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.is_superadmin:
            return "OWNER"

        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()

        if member:
            return member.role.upper()

        # Check workspace ownership
        workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        if workspace and workspace.owner_user_id == user_id:
            return "OWNER"

        return None

    @staticmethod
    def has_permission(db: Session, user_id: str, workspace_id: str, permission: str) -> bool:
        """Check if a user possesses a specific granular permission in a workspace."""
        role = RBACService.get_user_workspace_role(db, user_id, workspace_id)
        if not role:
            return False

        allowed_permissions = ROLE_PERMISSIONS.get(role, set())
        return permission in allowed_permissions

    @staticmethod
    def check_project_access(db: Session, user_id: str, project_id: str, required_level: str = "READ") -> Tuple[bool, str]:
        """Check if user has access to a specific project directly or via shared workspace."""
        # Check project share
        shares = db.query(ProjectShare).filter(ProjectShare.project_id == project_id).all()
        if not shares:
            # Default single-tenant / open workspace project access
            return True, "Default project access granted."

        for share in shares:
            role = RBACService.get_user_workspace_role(db, user_id, share.workspace_id)
            if role:
                level_order = {"READ": 1, "WRITE": 2, "ADMIN": 3}
                user_level_score = level_order.get(share.permission_level.upper(), 1)
                req_level_score = level_order.get(required_level.upper(), 1)

                if user_level_score >= req_level_score or role in ("OWNER", "ADMIN"):
                    return True, f"Project access granted via workspace {share.workspace_id} (level={share.permission_level})."

        return False, f"Access denied: User {user_id} lacks '{required_level}' permission for project {project_id}."

    @staticmethod
    def assign_workspace_role(db: Session, workspace_id: str, user_id: str, role: str, actor_user_id: str) -> WorkspaceMember:
        """Assign or update a member's role in a workspace."""
        if not RBACService.has_permission(db, actor_user_id, workspace_id, "member:manage"):
            raise PermissionError(f"Actor {actor_user_id} lacks 'member:manage' permission.")

        role_upper = role.upper()
        if role_upper not in ROLE_PERMISSIONS:
            raise ValueError(f"Invalid role '{role}'. Allowed roles: {list(ROLE_PERMISSIONS.keys())}")

        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id
        ).first()

        if member:
            member.role = role_upper
        else:
            member = WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role_upper)
            db.add(member)

        db.commit()
        db.refresh(member)

        # Log audit event
        SecurityService.log_audit_event(
            db=db,
            action_type="WORKSPACE_ROLE_ASSIGNED",
            severity="WARNING" if role_upper in ("OWNER", "ADMIN") else "INFO",
            agent_id="RBACService",
            details={
                "workspace_id": workspace_id,
                "target_user_id": user_id,
                "assigned_role": role_upper,
                "actor_user_id": actor_user_id,
            },
        )
        return member
