"""Vector store package."""
from app.rag.vector.qdrant_client import QdrantService, qdrant_service

__all__ = ["QdrantService", "qdrant_service"]
