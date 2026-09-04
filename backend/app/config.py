"""Configuration settings for the application."""
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings using Pydantic."""
    
    database_url: str = "sqlite+aiosqlite:///./radis_dev.db"
    redis_url: str = "redis://localhost:6379/0"
    
    llm_provider: Literal['mock', 'gemini'] = 'gemini'
    gemini_api_key: str = ''
    google_api_key: str = ''
    gemini_model: str = 'gemini-3.6-flash'
    
    search_provider: Literal['duckduckgo', 'google', 'tavily', 'mock'] = 'duckduckgo'
    google_search_api_key: str = ''
    google_search_engine_id: str = ''
    tavily_api_key: str = ''
    
    # Qdrant & Embedding RAG settings
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    embedding_provider: str = "mock"  # "openai", "huggingface", "mock"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_upload_size_mb: int = 50
    document_storage_path: str = "./uploads/documents"
    
    backend_host: str = '0.0.0.0'
    backend_port: int = 8000
    backend_reload: bool = True
    log_level: str = 'info'
    cors_origins: list[str] = ['http://localhost:3000', 'http://localhost:5173']
    
    # Phase 5: Self-Challenge & Critic Settings
    hypothesis_min_count: int = 3
    hypothesis_max_count: int = 7
    max_falsification_attempts: int = 5
    critic_severity_threshold: str = "HIGH"
    critic_confidence_threshold: float = 0.3
    max_replan_iterations: int = 3
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')



settings = Settings()
