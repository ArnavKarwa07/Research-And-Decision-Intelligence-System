import asyncio
import sys
from sqlalchemy import select, delete, func
from app.db.engine import async_session_factory
from app.models.session import Session
from app.models.query import Query
from app.models.source import Source
from app.models.evidence import Evidence
from app.models.agent_run import AgentRun
from app.models.document import Document
from app.models.artifact import Artifact
from app.models.monitoring import MonitoringJob, ResearchBaselineSnapshot
from app.models.project_memory import ProjectMemoryItem
from app.models.data_analysis import DataQueryRecord, VisualizationSpec, ReproducibleArtifact
from app.services.session_service import SessionService

async def cleanup(prune_tests: bool = False):
    async with async_session_factory() as db:
        session_service = SessionService(db)
        # Get all sessions
        res = await db.execute(select(Session).order_by(Session.created_at.desc()))
        sessions = list(res.scalars().all())
        print(f"Initial total sessions in DB: {len(sessions)}")

        deleted_count = 0
        for s in sessions:
            # Check if session has any queries
            q_res = await db.execute(select(func.count()).select_from(Query).where(Query.session_id == s.id))
            q_count = q_res.scalar_one()

            # 1. Empty untitled sessions
            is_empty = q_count == 0 and (not s.title or s.title in ["New Research Workspace", "Untitled Task"])
            
            # 2. Automated test run sessions
            is_test_session = False
            if prune_tests and s.title:
                is_test_session = (
                    s.title.startswith("Phase ") or
                    "Contract Test" in s.title or
                    "End-to-End" in s.title or
                    s.title in ["Test", "Test Session", "Check DB Session", "Debug Session", "Exhaustive QA Session"]
                )

            if is_empty or is_test_session:
                await session_service.delete_session(s.id)
                deleted_count += 1

        print(f"Cleaned up {deleted_count} empty or automated test sessions from DB.")

        res_remaining = await db.execute(select(func.count()).select_from(Session))
        print(f"Remaining sessions in DB: {res_remaining.scalar_one()}")

if __name__ == "__main__":
    prune_tests = "--prune-tests" in sys.argv or "--all" in sys.argv
    asyncio.run(cleanup(prune_tests=prune_tests))

