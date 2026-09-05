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

@router.patch('/{session_id}', response_model=SessionResponse)
@router.patch('/{session_id}/', response_model=SessionResponse)
@router.put('/{session_id}', response_model=SessionResponse)
@router.put('/{session_id}/', response_model=SessionResponse)
async def update_session(session_id: UUID, data: SessionCreate, db: AsyncSession = Depends(get_db)):
    """Update a session's title or details."""
    service = SessionService(db)
    if data.title:
        session = await service.update_session_title(session_id, data.title)
    else:
        session = await service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete('/{session_id}', status_code=status.HTTP_204_NO_CONTENT)
@router.delete('/{session_id}/', status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a session by ID."""
    service = SessionService(db)
    deleted = await service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return None


