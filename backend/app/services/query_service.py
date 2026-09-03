from uuid import UUID
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.query import Query
from app.models.evidence import Evidence
from app.schemas.query import QueryCreate, QueryStatus
from app.agents.graph import langgraph_app
from app.services.stream_service import stream_service, StreamEvent
from app.db.engine import async_session_factory

logger = logging.getLogger(__name__)

class QueryService:
    def __init__(self, db: AsyncSession, settings):
        self.db = db
        self.settings = settings

    async def create_query(self, session_id: UUID, data: QueryCreate) -> Query:
        query = Query(
            session_id=session_id,
            text=data.text,
            status='pending'
        )
        self.db.add(query)
        await self.db.commit()
        await self.db.refresh(query)
        return query

    async def get_query(self, query_id: UUID) -> Query | None:
        result = await self.db.execute(select(Query).where(Query.id == query_id))
        return result.scalar_one_or_none()

    async def run_research(self, query_id: UUID, mode: str = "deep") -> None:
        """Executes the LangGraph multi-agent workflow using an isolated background DB session."""
        logger.info(f"Starting background LangGraph workflow for query_id {query_id}")
        
        async with async_session_factory() as db:
            result = await db.execute(select(Query).where(Query.id == query_id))
            query = result.scalar_one_or_none()
            if not query:
                logger.error(f"Query {query_id} not found in database for background execution.")
                return

            query.status = 'running'
            db.add(query)
            await db.commit()
            await db.refresh(query)

            initial_state = {
                "query_id": str(query.id),
                "text": query.text,
                "mode": mode,
                "steps": [],
                "evidence": [],
                "search_queries": [],
                "summary": "",
                "confidence": 0.0,
                "is_complete": False,
                "current_step": 0
            }
            
            try:
                final_state = initial_state
                
                # Stream LangGraph state updates node-by-node
                async for output in langgraph_app.astream(initial_state):
                    for node_name, node_state in output.items():
                        logger.info(f"[LangGraph Stream] Node completed: '{node_name}'")
                        final_state.update(node_state)
                        
                        # Publish latest step to SSE clients
                        if node_state.get("steps"):
                            latest_step = node_state["steps"][-1]
                            step_event = StreamEvent(
                                event_type="step",
                                data=latest_step,
                                timestamp=datetime.now()
                            )
                            stream_service.publish(query.id, step_event)
                            
                # Persist collected evidence in Database
                collected_evidence = final_state.get("evidence", [])
                evidence_records = []
                for ev in collected_evidence:
                    db_ev = Evidence(
                        query_id=query.id,
                        evidence_type=ev.get("type", "FACT"),
                        content=ev.get("content", ""),
                        confidence=ev.get("confidence", 0.90)
                    )
                    db.add(db_ev)
                    evidence_records.append(ev)
                    
                summary_text = final_state.get("summary", "LangGraph investigation completed successfully.")
                confidence_val = final_state.get("confidence", 0.94)

                # Update Query status in DB
                query.status = 'completed'
                query.summary = summary_text
                query.confidence = confidence_val
                db.add(query)
                await db.commit()
                await db.refresh(query)

                # Emit final completion event to SSE listeners
                complete_event = StreamEvent(
                    event_type="complete",
                    data={
                        "query_id": str(query.id),
                        "summary": summary_text,
                        "confidence": confidence_val,
                        "evidence": evidence_records
                    },
                    timestamp=datetime.now()
                )
                stream_service.publish(query.id, complete_event)

            except Exception as e:
                logger.error(f"LangGraph workflow execution error for query {query.id}: {e}", exc_info=True)
                query.status = 'failed'
                db.add(query)
                await db.commit()
                
                error_event = StreamEvent(
                    event_type="error",
                    data={"message": f"LangGraph execution error: {str(e)}"},
                    timestamp=datetime.now()
                )
                stream_service.publish(query.id, error_event)

    async def get_evidence_for_query(self, query_id: UUID) -> list[Evidence]:
        result = await self.db.execute(select(Evidence).where(Evidence.query_id == query_id))
        return list(result.scalars().all())
