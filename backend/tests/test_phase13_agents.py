"""
Automated unit tests for Phase 13 Specialized Agents (ConnectorAgent & GovernanceAgent).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.connectors.connector_sync_service import ConnectorSyncService
from app.agents.connector_agent import ConnectorAgent
from app.agents.governance_agent import GovernanceAgent
from app.agents.agent_contracts import ConnectorAgentInput, GovernanceAgentInput


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_connector_agent_execution(test_db):
    connector = ConnectorSyncService.create_connector(
        db=test_db,
        workspace_id="ws_agent_test",
        provider_type="NOTION",
        name="Notion Test Connector",
    )

    agent = ConnectorAgent(db=test_db)
    agent_input = ConnectorAgentInput(
        connector_id=connector.id,
        workspace_id="ws_agent_test",
        sync_mode="FULL_SYNC",
    )

    output = agent.execute(agent_input)
    assert output.status in ("COMPLETED", "PARTIAL")
    assert output.items_processed >= 2
    assert "enterprise_connectors_ws_agent_test" in output.vector_collection


def test_governance_agent_execution(test_db):
    agent = GovernanceAgent(db=test_db)
    agent_input = GovernanceAgentInput(
        org_id="org_gov_test",
        workspace_id="ws_gov_test",
        audit_scope="FULL_COMPLIANCE_REPORT",
    )

    output = agent.execute(agent_input)
    assert output.audit_report_id is not None
    assert output.compliance_score >= 0.0
    assert len(output.recommendations) > 0
