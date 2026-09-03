"""API router for document ingestion and management."""
import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.dependencies import get_db
from app.db.engine import async_session_factory
from app.schemas.document import DocumentResponse, DocumentChunkResponse
from app.services.document_service import DocumentService
from app.services.stream_service import stream_service

router = APIRouter(tags=["documents"])


@router.post("/sessions/{session_id}/documents", response_model=DocumentResponse, status_code=202)
async def upload_document(
    session_id: UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Upload a document to a session and trigger asynchronous ingestion pipeline."""
    doc = await DocumentService.create_document(session_id=session_id, file=file, db=db)
    
    # Schedule background ingestion
    background_tasks.add_task(DocumentService.ingest_document_async, doc.id)
    
    return DocumentResponse.model_validate(doc)


@router.get("/sessions/{session_id}/documents", response_model=list[DocumentResponse])
async def list_session_documents(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentResponse]:
    """List all ingested documents for a session."""
    docs = await DocumentService.list_session_documents(session_id=session_id, db=db)
    return [DocumentResponse.model_validate(d) for d in docs]


@router.get("/documents/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Get details of a specific document."""
    doc = await DocumentService.get_document(document_id=document_id, db=db)
    return DocumentResponse.model_validate(doc)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Delete a document, its chunks, disk storage, and vector points from Qdrant."""
    return await DocumentService.delete_document(document_id=document_id, db=db)


@router.get("/documents/{document_id}/chunks", response_model=list[DocumentChunkResponse])
async def list_document_chunks(
    document_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> list[DocumentChunkResponse]:
    """List parsed chunks for a document with pagination."""
    # Ensure document exists
    await DocumentService.get_document(document_id=document_id, db=db)
    chunks = await DocumentService.get_document_chunks(
        document_id=document_id,
        db=db,
        skip=skip,
        limit=limit,
    )
    return [DocumentChunkResponse.model_validate(c) for c in chunks]


@router.get("/documents/{document_id}/stream")
async def stream_document_status(
    document_id: UUID,
    request: Request,
) -> EventSourceResponse:
    """SSE endpoint for streaming real-time document ingestion status progress."""
    async with async_session_factory() as db:
        doc = await DocumentService.get_document(document_id=document_id, db=db)
        target_doc_id = doc.id

    subscriber_id, event_generator = await stream_service.subscribe(target_doc_id)

    async def sse_generator():
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(anext(event_generator), timeout=1.0)
                    yield {
                        "event": event.event_type,
                        "data": event.model_dump_json(),
                    }
                except StopAsyncIteration:
                    break
                except asyncio.TimeoutError:
                    continue
        finally:
            stream_service.unsubscribe(target_doc_id, subscriber_id)

    return EventSourceResponse(sse_generator())
