from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.session import Session
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
        query = select(Session).order_by(Session.created_at.desc())
        
        if cursor:
            from datetime import datetime
            cursor_dt = datetime.fromisoformat(cursor)
            query = query.where(Session.created_at < cursor_dt)
            
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        sessions = list(result.scalars().all())
        
        count_result = await self.db.execute(select(func.count()).select_from(Session))
        total_count = count_result.scalar_one()
        
        next_cursor = sessions[-1].created_at.isoformat() if sessions else None
        
        return sessions, total_count, next_cursor

    async def update_session_status(self, session_id: UUID, status: str) -> Session | None:
        session = await self.get_session(session_id)
        if session:
            session.status = status
            await self.db.commit()
            await self.db.refresh(session)
        return session
