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
    
    search_provider: Literal['duckduckgo', 'google', 'tavily'] = 'duckduckgo'
    google_search_api_key: str = ''
    google_search_engine_id: str = ''
    tavily_api_key: str = ''
    
    backend_host: str = '0.0.0.0'
    backend_port: int = 8000
    backend_reload: bool = True
    log_level: str = 'info'
    cors_origins: list[str] = ['http://localhost:3000', 'http://localhost:5173']
    
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')


settings = Settings()
