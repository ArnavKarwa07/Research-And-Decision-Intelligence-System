from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.models.session import Session
from app.models.query import Query
from app.models.document import Document
from app.models.artifact import Artifact
from app.models.monitoring import MonitoringJob, ResearchBaselineSnapshot
from app.models.project_memory import ProjectMemoryItem
from app.models.source import Source
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.models.contradiction import Contradiction
from app.models.critique_report import CritiqueReport
from app.models.decision import Decision
from app.models.hypothesis import Hypothesis
from app.models.agent_run import AgentRun
from app.models.data_analysis import DataQueryRecord, VisualizationSpec, ReproducibleArtifact
from app.schemas.session import SessionCreate

class SessionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, data: SessionCreate) -> Session:
        session = Session(title=data.title)
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: UUID) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.id == session_id))
        return result.scalar_one_or_none()

    async def list_sessions(self, limit: int = 20, cursor: str | None = None) -> tuple[list[Session], int, str | None]:
        query = select(Session).order_by(Session.updated_at.desc())
        
        if cursor:
            from datetime import datetime
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.where(Session.updated_at < cursor_dt)
            
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        sessions = list(result.scalars().all())
        
        count_result = await self.db.execute(select(func.count()).select_from(Session))
        total_count = count_result.scalar_one()
        
        next_cursor = sessions[-1].updated_at.isoformat() if (sessions and sessions[-1].updated_at) else None
        
        return sessions, total_count, next_cursor

    async def update_session_status(self, session_id: UUID, status: str) -> Session | None:
        session = await self.get_session(session_id)
        if session:
            from datetime import datetime
            session.status = status
            session.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def update_session_title(self, session_id: UUID, title: str) -> Session | None:
        session = await self.get_session(session_id)
        if session:
            from datetime import datetime
            session.title = title
            session.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def delete_session(self, session_id: UUID) -> bool:
        session = await self.get_session(session_id)
        if not session:
            return False

        str_session_id = str(session_id)

        # 1. Fetch query IDs for this session
        q_result = await self.db.execute(select(Query.id).where(Query.session_id == session_id))
        query_ids = list(q_result.scalars().all())

        # 2. Delete child records referencing query_id
        if query_ids:
            for q_id in query_ids:
                await self.db.execute(delete(Source).where(Source.query_id == q_id))
                await self.db.execute(delete(Claim).where(Claim.query_id == q_id))
                await self.db.execute(delete(Evidence).where(Evidence.query_id == q_id))
                await self.db.execute(delete(Contradiction).where(Contradiction.query_id == q_id))
                await self.db.execute(delete(CritiqueReport).where(CritiqueReport.query_id == q_id))
                await self.db.execute(delete(Decision).where(Decision.query_id == q_id))
                await self.db.execute(delete(Hypothesis).where(Hypothesis.query_id == q_id))
                await self.db.execute(delete(AgentRun).where(AgentRun.query_id == q_id))
                await self.db.execute(delete(DataQueryRecord).where(DataQueryRecord.query_id == q_id))
                await self.db.execute(delete(VisualizationSpec).where(VisualizationSpec.query_id == q_id))
                await self.db.execute(delete(ReproducibleArtifact).where(ReproducibleArtifact.query_id == q_id))
                await self.db.execute(delete(Artifact).where(Artifact.query_id == q_id))

        # 3. Delete child records referencing session_id
        await self.db.execute(delete(MonitoringJob).where(MonitoringJob.session_id == session_id))
        await self.db.execute(delete(ResearchBaselineSnapshot).where(ResearchBaselineSnapshot.session_id == session_id))
        await self.db.execute(delete(ProjectMemoryItem).where(ProjectMemoryItem.session_id == session_id))
        await self.db.execute(delete(Document).where(Document.session_id == session_id))
        await self.db.execute(delete(Artifact).where(Artifact.session_id == session_id))
        await self.db.execute(delete(Query).where(Query.session_id == session_id))

        # 4. Delete session itself
        await self.db.delete(session)
        await self.db.commit()
        return True


