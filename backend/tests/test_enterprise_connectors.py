"""
Automated unit & integration tests for Enterprise Connectors Engine (Phase 13).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.enterprise_connector import EnterpriseConnector, ConnectorSyncJob, ConnectorItemLog
from app.services.connectors.base_connector import encrypt_credentials, decrypt_credentials
from app.services.connectors.google_drive_connector import GoogleDriveConnector
from app.services.connectors.notion_connector import NotionConnector
from app.services.connectors.slack_connector import SlackConnector
from app.services.connectors.gmail_connector import GmailConnector
from app.services.connectors.sharepoint_connector import SharePointConnector
from app.services.connectors.connector_sync_service import ConnectorSyncService


@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()


def test_credential_encryption_decryption():
    raw_creds = {"access_token": "secret_token_123", "client_secret": "my_secret"}
    encrypted = encrypt_credentials(raw_creds)
    assert encrypted.get("is_encrypted") is True
    assert "payload" in encrypted

    decrypted = decrypt_credentials(encrypted)
    assert decrypted.get("access_token") == "secret_token_123"
    assert decrypted.get("client_secret") == "my_secret"


def test_google_drive_connector_fetch_and_chunk():
    connector = GoogleDriveConnector("c1", "ws1", {"access_token": "mock_token"}, {"allow_mock_fallback": True})
    is_valid, msg = connector.validate_connection()
    assert is_valid is True

    items = connector.fetch_items(sync_mode="FULL_SYNC")
    assert len(items) >= 2
    doc = items[0]
    assert doc.external_id == "gdrive_doc_001"

    chunks = connector.chunk_item(doc, chunk_size=20, chunk_overlap=5)
    assert len(chunks) > 0
    assert chunks[0]["workspace_id"] == "ws1"


def test_notion_connector_fetch():
    connector = NotionConnector("c2", "ws1", {"notion_api_token": "secret_123"}, {"allow_mock_fallback": True})
    items = connector.fetch_items()
    assert len(items) >= 2
    assert "Security & Compliance" in items[0].title


def test_slack_connector_fetch():
    connector = SlackConnector("c3", "ws1", {"slack_bot_token": "xoxb-123"}, {"allow_mock_fallback": True})
    items = connector.fetch_items()
    assert len(items) >= 2
    assert items[0].item_type == "thread"


def test_gmail_connector_fetch():
    connector = GmailConnector("c4", "ws1", {"gmail_access_token": "token_123"}, {"allow_mock_fallback": True})
    items = connector.fetch_items()
    assert len(items) >= 2
    assert items[0].item_type == "email"


def test_sharepoint_connector_fetch():
    connector = SharePointConnector("c5", "ws1", {"graph_access_token": "token_123"}, {"allow_mock_fallback": True})
    items = connector.fetch_items()
    assert len(items) >= 2
    assert items[0].item_type == "file"


def test_connector_sync_service_lifecycle(test_db):
    connector = ConnectorSyncService.create_connector(
        db=test_db,
        workspace_id="ws_test",
        provider_type="GOOGLE_DRIVE",
        name="Test Drive",
        credentials={"access_token": "test"},
    )
    assert connector.id is not None
    assert connector.status == "ACTIVE"

    sync_job = ConnectorSyncService.execute_sync_job(db=test_db, connector_id=connector.id, job_type="FULL_SYNC")
    assert sync_job.status in ("COMPLETED", "PARTIAL")
    assert sync_job.items_processed >= 2

    health = ConnectorSyncService.get_connector_health(db=test_db, connector_id=connector.id)
    assert health["total_jobs"] == 1
    assert health["total_items_indexed"] >= 2
    assert health["rate_limit_status"] == "HEALTHY"
