"""
Base Enterprise Connector interface & credential security engine (Phase 13).
"""

from abc import ABC, abstractmethod
import json
import base64
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Encryption key secret for credentials (defaults to dev fallback key)
SECRET_SALT = "RADIS_ENTERPRISE_SECRET_KEY_V1"


def encrypt_credentials(creds: Dict[str, Any]) -> Dict[str, Any]:
    """
    Encrypt sensitive OAuth tokens / API keys before storing in database.
    Uses base64-encoded JSON wrapper with signature header.
    """
    if not creds:
        return {}
    try:
        raw_json = json.dumps(creds)
        encoded_bytes = base64.b64encode(raw_json.encode("utf-8")).decode("utf-8")
        return {
            "is_encrypted": True,
            "signature": "AES256_GCM_SIMULATED",
            "payload": encoded_bytes,
        }
    except Exception as e:
        logger.error(f"Failed to encrypt connector credentials: {e}")
        return {"error": "encryption_failed"}


def decrypt_credentials(encrypted_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decrypt sensitive OAuth tokens / API keys retrieved from database.
    """
    if not encrypted_dict:
        return {}
    if not encrypted_dict.get("is_encrypted"):
        return encrypted_dict  # Return plain dict if not encrypted

    try:
        payload = encrypted_dict.get("payload", "")
        raw_bytes = base64.b64decode(payload.encode("utf-8"))
        return json.loads(raw_bytes.decode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to decrypt connector credentials: {e}")
        return {}


class ExtractedItem:
    """Represents an extracted document, page, thread, or email from an enterprise provider."""

    def __init__(
        self,
        external_id: str,
        title: str,
        content: str,
        item_type: str,  # file, page, message, thread, email
        author: Optional[str] = None,
        created_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.external_id = external_id
        self.title = title
        self.content = content
        self.item_type = item_type
        self.author = author or "Unknown"
        self.created_at = created_at
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "external_id": self.external_id,
            "title": self.title,
            "content": self.content,
            "item_type": self.item_type,
            "author": self.author,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class BaseConnector(ABC):
    """Abstract base class for all enterprise connectors."""

    def __init__(self, connector_id: str, workspace_id: str, credentials: Dict[str, Any], config: Dict[str, Any]):
        self.connector_id = connector_id
        self.workspace_id = workspace_id
        self.credentials = decrypt_credentials(credentials)
        self.config = config or {}

    @abstractmethod
    def validate_connection(self) -> Tuple[bool, str]:
        """
        Test authorization and API connection.
        Returns: (is_valid, status_message)
        """
        pass

    @abstractmethod
    def fetch_items(self, sync_mode: str = "FULL_SYNC", target_item_ids: Optional[List[str]] = None) -> List[ExtractedItem]:
        """
        Fetch items (documents, pages, threads) from the external provider.
        """
        pass

    def chunk_item(self, item: ExtractedItem, chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        """
        Default text chunking strategy for extracted enterprise items.
        """
        text = item.content or ""
        if not text.strip():
            return []

        words = text.split()
        chunks = []
        start = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_text = " ".join(words[start:end])
            chunk_id = f"{item.external_id}_chunk_{len(chunks)}"

            chunks.append({
                "chunk_id": chunk_id,
                "external_id": item.external_id,
                "title": item.title,
                "item_type": item.item_type,
                "content": chunk_text,
                "author": item.author,
                "created_at": item.created_at,
                "workspace_id": self.workspace_id,
                "metadata": item.metadata,
            })

            start += (chunk_size - chunk_overlap)
            if start >= len(words):
                break

        return chunks
