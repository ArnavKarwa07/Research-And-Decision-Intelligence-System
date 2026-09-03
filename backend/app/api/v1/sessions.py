from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.session import SessionCreate, SessionResponse
from app.schemas.common import PaginatedResponse
from app.dependencies import get_db
from app.services.session_service import SessionService

router = APIRouter(prefix='/sessions', tags=['sessions'])

@router.post('/', response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(data: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Create a new research session."""
    service = SessionService(db)
    return await service.create_session(data)

@router.get('/', response_model=PaginatedResponse[SessionResponse])
async def list_sessions(limit: int = 20, cursor: str | None = None, db: AsyncSession = Depends(get_db)):
    """List sessions with cursor-based pagination."""
    service = SessionService(db)
    sessions, total, next_cursor = await service.list_sessions(limit=limit, cursor=cursor)
    
    return PaginatedResponse(
        items=sessions,
        total=total,
        cursor=next_cursor
    )

@router.get('/{session_id}', response_model=SessionResponse)
async def get_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a session by ID."""
    service = SessionService(db)
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session
