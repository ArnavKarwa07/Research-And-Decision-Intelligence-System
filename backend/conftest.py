import os
import pytest

# Force test environment variables to use mock providers and disable external API calls
os.environ["LLM_PROVIDER"] = "mock"
os.environ["SEARCH_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_phase7.db"
os.environ["QDRANT_URL"] = ""

from app.config import settings
settings.llm_provider = "mock"
settings.search_provider = "mock"
settings.embedding_provider = "mock"
settings.database_url = "sqlite+aiosqlite:///./test_phase7.db"
settings.qdrant_url = ""

import app.agents.graph as graph_module
graph_module.web_search_tool.provider = "mock"





