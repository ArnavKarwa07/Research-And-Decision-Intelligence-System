import os
import pytest

# Force test environment variables to use mock providers and disable external API calls
os.environ["LLM_PROVIDER"] = "mock"
os.environ["SEARCH_PROVIDER"] = "mock"
os.environ["EMBEDDING_PROVIDER"] = "mock"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

