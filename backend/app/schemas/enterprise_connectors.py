"""
Pydantic schemas for Enterprise Connectors, Sync Jobs, and Item Logs (Phase 13).
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ConnectorCreate(BaseModel):
    workspace_id: str = Field(..., description="ID of the workspace owning the connector")
    provider_type: str = Field(..., description="Provider type: GOOGLE_DRIVE, NOTION, SLACK, GMAIL, SHAREPOINT")
    name: str = Field(..., description="Human-readable name for the connector")
    auth_type: str = Field(default="OAUTH2", description="Authentication type: OAUTH2, SERVICE_ACCOUNT, TOKEN")
    credentials: Optional[Dict[str, Any]] = Field(default=None, description="OAuth tokens or API credentials")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Folder IDs, channel lists, or sync settings")


class ConnectorUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None  # ACTIVE, PAUSED, ERROR, REVOKED
    credentials: Optional[Dict[str, Any]] = None
    config: Optional[Dict[str, Any]] = None


class ConnectorResponse(BaseModel):
    id: str
    workspace_id: str
    provider_type: str
    name: str
    auth_type: str
    status: str
    config: Dict[str, Any]
    last_sync_at: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class SyncJobTriggerRequest(BaseModel):
    job_type: str = Field(default="FULL_SYNC", description="FULL_SYNC, DELTA_SYNC, WEBHOOK")


class SyncJobResponse(BaseModel):
    id: str
    connector_id: str
    workspace_id: str
    job_type: str
    status: str
    items_discovered: int
    items_processed: int
    items_failed: int
    rate_limit_hits: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None


class ConnectorItemLogResponse(BaseModel):
    id: str
    sync_job_id: str
    connector_id: str
    external_id: str
    item_name: str
    item_type: str
    status: str
    chunk_count: int
    vector_collection: Optional[str] = None
    error_details: Optional[str] = None
    synced_at: str


class ConnectorHealthStatus(BaseModel):
    connector_id: str
    provider_type: str
    name: str
    status: str
    last_sync_at: Optional[str] = None
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    total_items_indexed: int
    rate_limit_status: str
