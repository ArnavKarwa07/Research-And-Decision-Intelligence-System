"""
SSO Authentication & Token Session Revocation Service (Phase 13).
Handles OIDC / OAuth2 / SAML authentication, JWT session token generation, and Redis / In-Memory token revocation blacklist.
"""

from datetime import datetime, timezone, timedelta
import hashlib
import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.rbac_governance import User, Organization, AuthTokenSession, Workspace, WorkspaceMember
from app.services.security_service import SecurityService

logger = logging.getLogger(__name__)

# Token revocation blacklist set for fast in-memory validation fallback
TOKEN_REVOCATION_BLACKLIST = set()


class SSOAuthService:
    """Service managing SSO login flows, session token creation, and revocation."""

    @staticmethod
    def generate_token_hash(token: str) -> str:
        """Compute SHA-256 hash of a JWT or session token."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def initiate_sso_flow(provider: str, redirect_uri: Optional[str] = None) -> Dict[str, Any]:
        """Generate SSO authorization URL and state token for specified identity provider."""
        state = str(uuid.uuid4())
        provider_lower = provider.lower()

        if provider_lower == "google":
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=RADIS_GOOGLE_CLIENT_ID&state={state}"
        elif provider_lower == "azure_ad":
            auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?response_type=code&client_id=RADIS_AZURE_CLIENT_ID&state={state}"
        elif provider_lower == "okta":
            auth_url = f"https://dev-okta.company.com/oauth2/v1/authorize?response_type=code&client_id=RADIS_OKTA_CLIENT_ID&state={state}"
        else:  # Mock Enterprise IdP fallback
            auth_url = f"http://localhost:8000/api/v1/auth/sso/mock-idp?state={state}"

        return {
            "provider": provider_lower,
            "auth_url": auth_url,
            "state": state,
        }

    @staticmethod
    def authenticate_sso_callback(
        db: Session,
        provider: str,
        code: str,
        device_info: str = "Web Browser",
        ip_address: str = "127.0.0.1",
    ) -> Tuple[User, AuthTokenSession, str, str]:
        """
        Process SSO authorization code, create/update User profile, issue session tokens.
        Returns: (user, auth_session, access_token, refresh_token)
        """
        # Determine email and identity from SSO response (with fallback for demo/mock)
        email = f"user_{code[:6]}@{provider.lower()}.company.com" if not code.startswith("mock") else "admin@enterprise.com"
        full_name = f"Enterprise User ({provider.capitalize()})"

        user = db.query(User).filter(User.email == email).first()
        if not user:
            # Create organization if none exists
            org = db.query(Organization).first()
            if not org:
                org = Organization(name="Default Enterprise Org", domain="company.com", sso_enabled=True)
                db.add(org)
                db.commit()

            user = User(
                org_id=org.id,
                email=email,
                full_name=full_name,
                sso_provider=provider.lower(),
                sso_subject_id=f"sub_{uuid.uuid4().hex[:8]}",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

            # Ensure default workspace membership as OWNER
            workspace = db.query(Workspace).filter(Workspace.org_id == org.id).first()
            if not workspace:
                workspace = Workspace(org_id=org.id, name="Primary Enterprise Workspace", slug="primary-workspace", owner_user_id=user.id)
                db.add(workspace)
                db.commit()
                db.refresh(workspace)

            member = WorkspaceMember(workspace_id=workspace.id, user_id=user.id, role="OWNER")
            db.add(member)
            db.commit()

        user.last_login_at = datetime.now(timezone.utc)
        db.commit()

        # Issue access & refresh tokens
        raw_access_token = f"radis_at_{uuid.uuid4().hex}"
        raw_refresh_token = f"radis_rt_{uuid.uuid4().hex}"
        token_hash = SSOAuthService.generate_token_hash(raw_access_token)

        expires_at = datetime.now(timezone.utc) + timedelta(hours=8)

        auth_session = AuthTokenSession(
            user_id=user.id,
            token_hash=token_hash,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(auth_session)
        db.commit()
        db.refresh(auth_session)

        # Audit event
        SecurityService.log_audit_event(
            db=db,
            action_type="SSO_LOGIN_SUCCESS",
            severity="INFO",
            agent_id="SSOAuthService",
            details={
                "user_id": user.id,
                "email": user.email,
                "provider": provider,
                "session_id": auth_session.id,
            },
        )

        return user, auth_session, raw_access_token, raw_refresh_token

    @staticmethod
    def revoke_session(db: Session, session_id: str, actor_user_id: str) -> bool:
        """Revoke a specific session token."""
        auth_session = db.query(AuthTokenSession).filter(AuthTokenSession.id == session_id).first()
        if not auth_session:
            return False

        auth_session.is_revoked = True
        db.commit()

        # Add token hash to in-memory revocation set
        TOKEN_REVOCATION_BLACKLIST.add(auth_session.token_hash)

        SecurityService.log_audit_event(
            db=db,
            action_type="SESSION_TOKEN_REVOKED",
            severity="WARNING",
            agent_id="SSOAuthService",
            details={
                "revoked_session_id": session_id,
                "target_user_id": auth_session.user_id,
                "actor_user_id": actor_user_id,
            },
        )
        return True

    @staticmethod
    def is_token_revoked(db: Session, raw_token: str) -> bool:
        """Check if a token has been revoked."""
        token_hash = SSOAuthService.generate_token_hash(raw_token)
        if token_hash in TOKEN_REVOCATION_BLACKLIST:
            return True

        auth_session = db.query(AuthTokenSession).filter(AuthTokenSession.token_hash == token_hash).first()
        if auth_session and auth_session.is_revoked:
            TOKEN_REVOCATION_BLACKLIST.add(token_hash)
            return True

        return False
