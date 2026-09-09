import asyncio
import uuid
from app.db.engine import async_session_factory
from app.services.query_service import QueryService
from app.services.session_service import SessionService
from app.config import settings

async def main():
    async with async_session_factory() as db:
        s_service = SessionService(db)
        sessions, total, cursor = await s_service.list_sessions(limit=20)
        print(f"Total sessions: {total}, Listed: {len(sessions)}")
        
        q_service = QueryService(db, settings)
        for s in sessions[:10]:
            queries = await q_service.get_session_queries(s.id)
            print(f"Session {s.id} | Title: '{s.title}' | Queries: {len(queries)}")
            for q in queries:
                print(f"   -> Query {q.id} | Text: '{q.text[:40]}' | Status: {q.status} | Plan: {q.research_plan is not None}")

if __name__ == '__main__':
    asyncio.run(main())
