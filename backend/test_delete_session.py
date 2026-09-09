import asyncio
from app.db.engine import async_session_factory
from app.services.session_service import SessionService

async def main():
    async with async_session_factory() as db:
        svc = SessionService(db)
        sessions, total, _ = await svc.list_sessions(limit=50)
        print(f"Total sessions in database: {total}")
        for s in sessions:
            print(f"ID: {s.id} | Title: '{s.title}' | Status: {s.status}")

        if sessions:
            first_id = sessions[0].id
            print(f"\nAttempting to delete session {first_id}...")
            try:
                success = await svc.delete_session(first_id)
                print(f"Delete success: {success}")
            except Exception as e:
                print(f"Delete FAILED with exception: {e}")

if __name__ == "__main__":
    asyncio.run(main())
