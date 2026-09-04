"""
ConnectorAgent implementation (Phase 13 Enterprise Connectors Engine).
Specialized subagent executing enterprise connector data ingestion, text chunking, and Qdrant vector embedding.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.agents.agent_contracts import ConnectorAgentInput, ConnectorAgentOutput
from app.services.connectors.connector_sync_service import ConnectorSyncService

logger = logging.getLogger(__name__)


class ConnectorAgent:
    """Specialized Agent for Enterprise Data Connector Ingestion & Vector Embedding."""

    def __init__(self, db: Session):
        self.db = db

    def execute(self, agent_input: ConnectorAgentInput) -> ConnectorAgentOutput:
        """Run ConnectorAgent data ingestion and vector indexing task."""
        logger.info(f"[CONNECTOR_AGENT] Running sync for connector {agent_input.connector_id} (workspace={agent_input.workspace_id})")

        try:
            sync_job = ConnectorSyncService.execute_sync_job(
                db=self.db,
                connector_id=agent_input.connector_id,
                job_type=agent_input.sync_mode,
                target_item_ids=agent_input.target_item_ids,
            )

            collection_name = f"enterprise_connectors_{agent_input.workspace_id}"

            return ConnectorAgentOutput(
                sync_job_id=sync_job.id,
                connector_id=agent_input.connector_id,
                workspace_id=agent_input.workspace_id,
                status=sync_job.status,
                items_processed=sync_job.items_processed,
                items_failed=sync_job.items_failed,
                chunks_indexed=sync_job.items_processed * 4,  # Estimated 4 chunks per item
                vector_collection=collection_name,
                rate_limit_encountered=sync_job.rate_limit_hits > 0,
                stop_reason="OBJECTIVE_SATISFIED",
                summary_message=(
                    f"Connector sync job '{sync_job.id}' completed with status '{sync_job.status}'. "
                    f"Processed {sync_job.items_processed} items into Qdrant collection '{collection_name}'."
                ),
            )

        except Exception as e:
            logger.error(f"[CONNECTOR_AGENT] Failed: {e}")
            return ConnectorAgentOutput(
                sync_job_id="failed_job",
                connector_id=agent_input.connector_id,
                workspace_id=agent_input.workspace_id,
                status="FAILED",
                stop_reason="EXECUTION_ERROR",
                summary_message=f"Connector agent failed: {e}",
                error_message=str(e),
            )
