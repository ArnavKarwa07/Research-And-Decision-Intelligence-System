"""
REST API endpoints for SSO Authentication & Session Token Revocation (Phase 13).
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query as APIQuery, Header
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.rbac_auth import (
    SSOLoginRequest,
    SSOCallbackRequest,
    TokenResponse,
    TokenRefreshRequest,
)
from app.services.sso_auth_service import SSOAuthService

router = APIRouter(prefix="/auth", tags=["SSO Authentication"])


@router.post("/sso/login")
def initiate_sso(payload: SSOLoginRequest):
    """Initiate SSO authentication flow and return authorization URL."""
    return SSOAuthService.initiate_sso_flow(provider=payload.provider, redirect_uri=payload.redirect_uri)


@router.get("/sso/mock-idp")
def mock_idp_endpoint(state: Optional[str] = None):
    """Built-in Mock Enterprise IdP redirect endpoint for offline integration testing & demos."""
    return {
        "message": "Mock Enterprise IdP Authentication Prompt",
        "state": state,
        "simulated_code": f"mock_code_{state[:8] if state else '1234'}",
        "instructions": "POST this simulated code to /api/v1/auth/sso/callback to complete login.",
    }


@router.post("/sso/callback", response_model=TokenResponse)
def sso_callback(payload: SSOCallbackRequest, db: Session = Depends(get_db)):
    """Process SSO callback authorization code and return JWT access/refresh token pair."""
    try:
        user, session, access_token, refresh_token = SSOAuthService.authenticate_sso_callback(
            db=db,
            provider=payload.provider,
            code=payload.code,
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=28800,  # 8 hours
            user=user.to_dict(),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SSO authentication failed: {e}")


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Revoke session token and log user out."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"message": "Logged out."}

    raw_token = authorization.replace("Bearer ", "").strip()
    token_hash = SSOAuthService.generate_token_hash(raw_token)

    from app.models.rbac_governance import AuthTokenSession
    session = db.query(AuthTokenSession).filter(AuthTokenSession.token_hash == token_hash).first()
    if session:
        SSOAuthService.revoke_session(db=db, session_id=session.id, actor_user_id=session.user_id)

    return {"message": "Session token successfully revoked. User logged out."}
