from fastapi import APIRouter
from app.api.v1 import sessions, queries, stream, evidence

api_v1_router = APIRouter(prefix='/api/v1', tags=['v1'])
api_v1_router.include_router(sessions.router)
api_v1_router.include_router(queries.router)
api_v1_router.include_router(stream.router)
api_v1_router.include_router(evidence.router)
