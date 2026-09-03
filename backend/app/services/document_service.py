"""Document Service for managing document upload, async ingestion pipeline, and chunk/vector retrieval."""
import os
import hashlib
import uuid
import logging
from typing import Any
from fastapi import UploadFile, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.engine import async_session_factory
from app.models.document import Document, DocumentChunk, VectorCollection
from app.models.session import Session
from app.rag.parsers.factory import DocumentParserFactory
from app.rag.chunking.semantic_chunker import SemanticChunker
from app.rag.embeddings.provider import get_embedding_provider
from app.rag.vector.qdrant_client import qdrant_service
from app.services.stream_service import emit_document_status_updated

logger = logging.getLogger(__name__)


class DocumentService:
    """Service handling document storage, async ingestion pipeline, and database/Qdrant sync."""

    @staticmethod
    async def create_document(
        session_id: uuid.UUID,
        file: UploadFile,
        db: AsyncSession,
    ) -> Document:
        """Validate, store uploaded file on disk, and create Document DB record in 'queued' state."""
        # Check session exists
        session_res = await db.execute(select(Session).where(Session.id == session_id))
        session = session_res.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        # Sanitize filename (BUG-CRIT-01)
        safe_filename = os.path.basename(file.filename or "uploaded_document")
        mime_type = file.content_type or "application/octet-stream"

        # Validate file format against DocumentParserFactory BEFORE saving to disk (BUG-HIGH-06)
        try:
            DocumentParserFactory.get_parser(mime_type=mime_type, file_path=safe_filename)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported document format: {exc}"
            )

        # Stream upload bytes to disk in 1MB chunks (BUG-MED-11)
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        storage_dir = os.path.join(settings.document_storage_path, str(session_id))
        os.makedirs(storage_dir, exist_ok=True)

        doc_id = uuid.uuid4()
        file_path = os.path.join(storage_dir, f"{doc_id}_{safe_filename}")

        chunk_size = 1024 * 1024
        hasher = hashlib.sha256()
        total_bytes = 0

        try:
            with open(file_path, "wb") as f:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise HTTPException(
                            status_code=400,
                            detail=f"File size exceeds maximum allowed limit of {settings.max_upload_size_mb} MB"
                        )
                    hasher.update(chunk)
                    f.write(chunk)
        except Exception:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except OSError:
                    pass
            raise

        file_hash = hasher.hexdigest()

        # Create Document record
        doc = Document(
            id=doc_id,
            session_id=session_id,
            filename=safe_filename,
            mime_type=mime_type,
            file_path=file_path,
            file_size=total_bytes,
            file_hash=file_hash,
            metadata_json={"original_filename": safe_filename},
            status="queued",
            chunk_count=0,
        )

        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        emit_document_status_updated(
            document_id=doc.id,
            document_data={
                "document_id": str(doc.id),
                "session_id": str(doc.session_id),
                "filename": doc.filename,
                "status": doc.status,
                "chunk_count": doc.chunk_count,
            },
        )

        return doc

    @staticmethod
    async def ingest_document_async(document_id: uuid.UUID | str, db: AsyncSession | None = None) -> None:
        """Asynchronous ingestion pipeline task: PARSE -> CHUNK -> EMBED -> STORE IN QDRANT + DB."""
        if isinstance(document_id, str):
            document_id = uuid.UUID(document_id)

        # If no session passed, create standalone AsyncSession
        if db is None:
            async with async_session_factory() as session:
                await DocumentService._process_ingestion(document_id, session)
        else:
            await DocumentService._process_ingestion(document_id, db)

    @staticmethod
    async def _process_ingestion(document_id: uuid.UUID, db: AsyncSession) -> None:
        doc_res = await db.execute(select(Document).where(Document.id == document_id))
        doc = doc_res.scalar_one_or_none()

        if not doc:
            logger.error(f"Document {document_id} not found for ingestion pipeline.")
            return

        try:
            # Stage 1: PARSING
            doc.status = "parsing"
            await db.commit()
            emit_document_status_updated(doc.id, {"document_id": str(doc.id), "status": doc.status})

            parser = DocumentParserFactory.get_parser(mime_type=doc.mime_type, file_path=doc.file_path)
            parsed_doc = parser.parse(doc.file_path)

            # Stage 2: CHUNKING
            doc.status = "chunking"
            await db.commit()
            emit_document_status_updated(doc.id, {"document_id": str(doc.id), "status": doc.status})

            chunker = SemanticChunker(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
            chunk_results = chunker.chunk_document(parsed_doc)

            # Save chunks to DB with parent-child linkage
            db_chunks: list[DocumentChunk] = []
            chunk_idx_to_db_chunk: dict[int, DocumentChunk] = {}

            # First pass: create DocumentChunk instances
            for cr in chunk_results:
                chunk_obj = DocumentChunk(
                    id=uuid.uuid4(),
                    document_id=doc.id,
                    chunk_index=cr.chunk_index,
                    content=cr.content,
                    content_hash=cr.content_hash,
                    token_count=cr.token_count,
                    page_number=cr.page_number,
                    section_heading=cr.section_heading,
                    start_offset=cr.start_offset,
                    end_offset=cr.end_offset,
                    metadata_json=cr.metadata,
                )
                db.add(chunk_obj)
                db_chunks.append(chunk_obj)
                chunk_idx_to_db_chunk[cr.chunk_index] = chunk_obj

            await db.flush()

            # Second pass: set parent_chunk_id
            for cr in chunk_results:
                if cr.parent_chunk_index is not None and cr.parent_chunk_index in chunk_idx_to_db_chunk:
                    parent_obj = chunk_idx_to_db_chunk[cr.parent_chunk_index]
                    child_obj = chunk_idx_to_db_chunk[cr.chunk_index]
                    child_obj.parent_chunk_id = parent_obj.id

            await db.commit()

            # Stage 3: EMBEDDING
            doc.status = "embedding"
            await db.commit()
            emit_document_status_updated(doc.id, {"document_id": str(doc.id), "status": doc.status})

            provider = get_embedding_provider()
            chunk_texts = [c.content for c in db_chunks]
            embeddings = await provider.embed_texts(chunk_texts)

            # Stage 4: STORE IN QDRANT + DB
            collection_name = f"session_{doc.session_id.hex}"
            dimension = provider.dimension
            qdrant_service.ensure_collection(collection_name=collection_name, dimension=dimension)

            points: list[dict[str, Any]] = []
            for chunk_obj, vector in zip(db_chunks, embeddings):
                emb_id = str(uuid.uuid4())
                chunk_obj.embedding_id = emb_id

                points.append({
                    "id": emb_id,
                    "vector": vector,
                    "payload": {
                        "chunk_id": str(chunk_obj.id),
                        "document_id": str(doc.id),
                        "session_id": str(doc.session_id),
                        "content": chunk_obj.content,
                        "page_number": chunk_obj.page_number,
                        "section_heading": chunk_obj.section_heading,
                        "start_offset": chunk_obj.start_offset,
                        "end_offset": chunk_obj.end_offset,
                        "content_hash": chunk_obj.content_hash,
                        "token_count": chunk_obj.token_count,
                        "chunk_index": chunk_obj.chunk_index,
                        "parent_chunk_id": str(chunk_obj.parent_chunk_id) if chunk_obj.parent_chunk_id else None,
                    },
                })

            qdrant_service.upsert_points(collection_name=collection_name, points=points)

            # Update or create VectorCollection tracking entry
            vc_res = await db.execute(
                select(VectorCollection).where(VectorCollection.session_id == doc.session_id)
            )
            vec_coll = vc_res.scalar_one_or_none()
            if not vec_coll:
                vec_coll = VectorCollection(
                    id=uuid.uuid4(),
                    session_id=doc.session_id,
                    name=collection_name,
                    dimension=dimension,
                    distance_metric="cosine",
                    chunk_count=len(db_chunks),
                )
                db.add(vec_coll)
            else:
                vec_coll.chunk_count += len(db_chunks)

            # Finalize Document status
            doc.status = "stored"
            doc.chunk_count = len(db_chunks)
            await db.commit()

            emit_document_status_updated(
                doc.id,
                {
                    "document_id": str(doc.id),
                    "status": "stored",
                    "chunk_count": doc.chunk_count,
                },
            )

        except Exception as e:
            logger.exception(f"Error during ingestion pipeline for document {document_id}: {e}")
            await db.rollback()
            doc_res = await db.execute(select(Document).where(Document.id == document_id))
            err_doc = doc_res.scalar_one_or_none()
            if err_doc:
                err_doc.status = "failed"
                err_doc.error_message = str(e)
                await db.commit()
                emit_document_status_updated(
                    err_doc.id,
                    {
                        "document_id": str(err_doc.id),
                        "status": "failed",
                        "error_message": str(e),
                    },
                )

    @staticmethod
    async def get_document(document_id: uuid.UUID, db: AsyncSession) -> Document:
        """Fetch document details by UUID."""
        res = await db.execute(select(Document).where(Document.id == document_id))
        doc = res.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        return doc

    @staticmethod
    async def list_session_documents(session_id: uuid.UUID, db: AsyncSession) -> list[Document]:
        """List all documents for a session."""
        res = await db.execute(select(Document).where(Document.session_id == session_id))
        return list(res.scalars().all())

    @staticmethod
    async def delete_document(document_id: uuid.UUID, db: AsyncSession) -> dict[str, str]:
        """Delete document record, its chunks, stored file on disk, and Qdrant points."""
        doc = await DocumentService.get_document(document_id, db)
        collection_name = f"session_{doc.session_id.hex}"

        # Fetch chunk embedding IDs to delete from Qdrant
        chunk_res = await db.execute(
            select(DocumentChunk.embedding_id).where(DocumentChunk.document_id == document_id)
        )
        embedding_ids = [e for e in chunk_res.scalars().all() if e]
        if embedding_ids:
            qdrant_service.delete_points(collection_name=collection_name, point_ids=embedding_ids)

        # Delete file from disk
        if os.path.exists(doc.file_path):
            try:
                os.remove(doc.file_path)
            except OSError as e:
                logger.warning(f"Could not delete document file {doc.file_path}: {e}")

        # Delete from DB (cascades to chunks)
        await db.delete(doc)
        await db.commit()

        return {"message": f"Document {document_id} deleted successfully"}

    @staticmethod
    async def get_document_chunks(
        document_id: uuid.UUID,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DocumentChunk]:
        """List chunks for a document with pagination."""
        res = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        return list(res.scalars().all())
