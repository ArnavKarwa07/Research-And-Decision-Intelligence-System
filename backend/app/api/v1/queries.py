from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.query import QueryCreate, QueryResponse
from app.dependencies import get_db, get_settings
from app.services.query_service import QueryService
from app.services.session_service import SessionService

router = APIRouter(prefix='/sessions/{session_id}/queries', tags=['queries'])

@router.post('', response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
@router.post('/', response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
async def create_query(
    session_id: UUID, 
    data: QueryCreate, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db), 
    settings = Depends(get_settings)
):
    """Create a query and start research in the background via LangGraph."""
    session_service = SessionService(db)
    session = await session_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    query_service = QueryService(db, settings)
    query = await query_service.create_query(session_id, data)
    
    background_tasks.add_task(query_service.run_research, query.id, data.mode)
    
    return query

@router.get('', response_model=list[QueryResponse])
@router.get('/', response_model=list[QueryResponse])
async def list_session_queries(session_id: UUID, db: AsyncSession = Depends(get_db), settings = Depends(get_settings)):
    """List all queries for a research session."""
    query_service = QueryService(db, settings)
    return await query_service.get_session_queries(session_id)

@router.get('/{query_id}', response_model=QueryResponse)
async def get_query(session_id: UUID, query_id: UUID, db: AsyncSession = Depends(get_db), settings = Depends(get_settings)):
    """Get a query by ID."""
    query_service = QueryService(db, settings)
    query = await query_service.get_query(query_id)
    if not query or query.session_id != session_id:
        raise HTTPException(status_code=404, detail="Query not found")
    return query
