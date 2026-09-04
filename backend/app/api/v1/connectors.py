"""
REST API endpoints for Enterprise Connectors & Sync Monitoring (Phase 13).
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query as APIQuery
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.enterprise_connectors import (
    ConnectorCreate,
    ConnectorUpdate,
    ConnectorResponse,
    SyncJobTriggerRequest,
    SyncJobResponse,
    ConnectorItemLogResponse,
    ConnectorHealthStatus,
)
from app.models.enterprise_connector import EnterpriseConnector, ConnectorSyncJob, ConnectorItemLog
from app.services.connectors.connector_sync_service import ConnectorSyncService
from app.agents.connector_agent import ConnectorAgent
from app.agents.agent_contracts import ConnectorAgentInput

router = APIRouter(prefix="/connectors", tags=["Enterprise Connectors"])


@router.post("", response_model=ConnectorResponse, status_code=201)
def create_connector(payload: ConnectorCreate, db: Session = Depends(get_db)):
    """Create and configure a new enterprise connector."""
    try:
        connector = ConnectorSyncService.create_connector(
            db=db,
            workspace_id=payload.workspace_id,
            provider_type=payload.provider_type,
            name=payload.name,
            auth_type=payload.auth_type,
            credentials=payload.credentials,
            config=payload.config,
        )
        return connector.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create connector: {e}")


@router.get("", response_model=List[ConnectorResponse])
def list_connectors(
    workspace_id: Optional[str] = APIQuery(None),
    provider_type: Optional[str] = APIQuery(None),
    db: Session = Depends(get_db)
):
    """List all enterprise connectors filtered by workspace or provider type."""
    query = db.query(EnterpriseConnector)
    if workspace_id:
        query = query.filter(EnterpriseConnector.workspace_id == workspace_id)
    if provider_type:
        query = query.filter(EnterpriseConnector.provider_type == provider_type.upper())

    connectors = query.all()
    return [c.to_dict() for c in connectors]


@router.get("/{connector_id}", response_model=ConnectorResponse)
def get_connector(connector_id: str, db: Session = Depends(get_db)):
    """Retrieve details for a specific connector by ID."""
    connector = db.query(EnterpriseConnector).filter(EnterpriseConnector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found.")
    return connector.to_dict()


@router.patch("/{connector_id}", response_model=ConnectorResponse)
def update_connector(connector_id: str, payload: ConnectorUpdate, db: Session = Depends(get_db)):
    """Update connector settings, status, or credentials."""
    connector = db.query(EnterpriseConnector).filter(EnterpriseConnector.id == connector_id).first()
    if not connector:
        raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found.")

    if payload.name is not None:
        connector.name = payload.name
    if payload.status is not None:
        connector.status = payload.status.upper()
    if payload.config is not None:
        connector.config = payload.config

    db.commit()
    db.refresh(connector)
    return connector.to_dict()


@router.post("/{connector_id}/sync", response_model=SyncJobResponse)
def trigger_sync_job(
    connector_id: str,
    payload: Optional[SyncJobTriggerRequest] = None,
    db: Session = Depends(get_db)
):
    """Trigger a manual sync job for an enterprise connector."""
    job_type = payload.job_type if payload else "FULL_SYNC"
    try:
        agent = ConnectorAgent(db=db)
        connector = db.query(EnterpriseConnector).filter(EnterpriseConnector.id == connector_id).first()
        if not connector:
            raise HTTPException(status_code=404, detail=f"Connector {connector_id} not found.")

        agent_input = ConnectorAgentInput(
            connector_id=connector.id,
            workspace_id=connector.workspace_id,
            sync_mode=job_type,
        )
        output = agent.execute(agent_input)

        sync_job = db.query(ConnectorSyncJob).filter(ConnectorSyncJob.id == output.sync_job_id).first()
        if not sync_job:
            # Fallback direct service execution
            sync_job = ConnectorSyncService.execute_sync_job(db=db, connector_id=connector_id, job_type=job_type)

        return sync_job.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sync execution failed: {e}")


@router.get("/{connector_id}/jobs", response_model=List[SyncJobResponse])
def list_sync_jobs(connector_id: str, db: Session = Depends(get_db)):
    """List all sync jobs for a connector."""
    jobs = db.query(ConnectorSyncJob).filter(ConnectorSyncJob.connector_id == connector_id).order_by(ConnectorSyncJob.created_at.desc()).all()
    return [j.to_dict() for j in jobs]


@router.get("/{connector_id}/health", response_model=ConnectorHealthStatus)
def get_connector_health(connector_id: str, db: Session = Depends(get_db)):
    """Get sync health and rate limit metrics for a connector."""
    try:
        return ConnectorSyncService.get_connector_health(db=db, connector_id=connector_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
