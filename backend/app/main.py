"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator

from app.config import Settings
from app.db.engine import init_db

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for the FastAPI app."""
    # Initialize DB on startup
    await init_db()
    yield

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = Settings()
    
    app = FastAPI(
        title="radis-backend",
        version="0.1.0",
        lifespan=lifespan
    )
    
    cors_origins = list(settings.cors_origins) + ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    try:
        from app.api.v1.router import api_v1_router
        app.include_router(api_v1_router)
    except ImportError:
        pass
        
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok"}
        
    return app

app = create_app()
