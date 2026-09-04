"""
SQLAlchemy models for Enterprise Connectors, Sync Jobs, and Item Logs (Phase 13).
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer, ForeignKey, Boolean
from app.models.base import Base, TimestampMixin


class EnterpriseConnector(Base, TimestampMixin):
    __tablename__ = "enterprise_connectors"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), nullable=False, index=True)
    provider_type = Column(String(50), nullable=False, index=True)  # GOOGLE_DRIVE, NOTION, SLACK, GMAIL, SHAREPOINT
    name = Column(String(255), nullable=False)
    auth_type = Column(String(50), nullable=False, default="OAUTH2")  # OAUTH2, SERVICE_ACCOUNT, TOKEN
    credentials_encrypted = Column(JSON, nullable=True)  # Encrypted OAuth tokens / API keys
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)  # ACTIVE, PAUSED, ERROR, REVOKED
    config = Column(JSON, nullable=True)  # Folder filters, sync interval, channel IDs, etc.
    last_sync_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "workspace_id": self.workspace_id,
            "provider_type": self.provider_type,
            "name": self.name,
            "auth_type": self.auth_type,
            "status": self.status,
            "config": self.config or {},
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ConnectorSyncJob(Base, TimestampMixin):
    __tablename__ = "connector_sync_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    connector_id = Column(String(36), ForeignKey("enterprise_connectors.id", ondelete="CASCADE"), nullable=False, index=True)
    workspace_id = Column(String(36), nullable=False, index=True)
    job_type = Column(String(50), nullable=False, default="FULL_SYNC")  # FULL_SYNC, DELTA_SYNC, WEBHOOK
    status = Column(String(50), nullable=False, default="QUEUED", index=True)  # QUEUED, SYNCING, COMPLETED, FAILED, CANCELLED
    items_discovered = Column(Integer, nullable=False, default=0)
    items_processed = Column(Integer, nullable=False, default=0)
    items_failed = Column(Integer, nullable=False, default=0)
    rate_limit_hits = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "connector_id": self.connector_id,
            "workspace_id": self.workspace_id,
            "job_type": self.job_type,
            "status": self.status,
            "items_discovered": self.items_discovered,
            "items_processed": self.items_processed,
            "items_failed": self.items_failed,
            "rate_limit_hits": self.rate_limit_hits,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ConnectorItemLog(Base):
    __tablename__ = "connector_item_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    sync_job_id = Column(String(36), ForeignKey("connector_sync_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    connector_id = Column(String(36), nullable=False, index=True)
    external_id = Column(String(255), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    item_type = Column(String(50), nullable=False, default="file")  # file, page, message, thread, email
    status = Column(String(50), nullable=False, default="INDEXED")  # INDEXED, SKIPPED, FAILED
    chunk_count = Column(Integer, nullable=False, default=0)
    vector_collection = Column(String(100), nullable=True)
    error_details = Column(Text, nullable=True)
    synced_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            "id": self.id,
            "sync_job_id": self.sync_job_id,
            "connector_id": self.connector_id,
            "external_id": self.external_id,
            "item_name": self.item_name,
            "item_type": self.item_type,
            "status": self.status,
            "chunk_count": self.chunk_count,
            "vector_collection": self.vector_collection,
            "error_details": self.error_details,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }
