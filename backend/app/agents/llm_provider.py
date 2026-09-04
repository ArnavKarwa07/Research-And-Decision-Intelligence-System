from typing import Literal, Any, Optional
from pydantic import BaseModel
from abc import ABC, abstractmethod
import os
import logging
import json

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from app.config import settings

logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: Literal['system', 'user', 'assistant']
    content: str

class LLMResponse(BaseModel):
    content: str
    tokens_used: int
    model: str
    finish_reason: str = 'stop'

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        """Generate unstructured text response."""
        ...
        
    @abstractmethod
    async def generate_structured(self, messages: list[Message], response_schema: type[BaseModel], **kwargs: Any) -> BaseModel:
        """Generate structured response matching the schema."""
        ...

class MockProvider(LLMProvider):
    """Mock provider for testing. Returns canned responses."""
    
    def __init__(self, default_response: str = "Mock response"):
        self.default_response = default_response

    async def generate(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        logger.debug(f"Mock generation called with {len(messages)} messages")
        last_user_msg = next((m.content for m in reversed(messages) if m.role == 'user'), "Hello")
        
        return LLMResponse(
            content=f"Mocking response to: {last_user_msg[:20]}...",
            tokens_used=42,
            model="mock-v1"
        )

    async def generate_structured(self, messages: list[Message], response_schema: type[BaseModel], **kwargs: Any) -> BaseModel:
        logger.debug(f"Mock structured generation for schema {response_schema.__name__}")
        try:
            return response_schema()
        except Exception:
            fields = {}
            for k, f in response_schema.model_fields.items():
                if f.annotation == str:
                    fields[k] = "mock"
                elif f.annotation == int or f.annotation == float:
                    fields[k] = 0
                elif f.annotation == bool:
                    fields[k] = False
                elif f.annotation == dict:
                    fields[k] = {}
                elif f.annotation == list:
                    fields[k] = []
                else:
                    fields[k] = None
            return response_schema(**fields)

class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using ChatGoogleGenerativeAI from langchain_google_genai.
    """
    
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY") or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model or "gemini-2.5-flash"
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. GeminiProvider will fail if invoked.")
            
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            GEMINI_API_KEY=self.api_key,
            temperature=0.2,
        )

    def _convert_messages(self, messages: list[Message]) -> list[BaseMessage]:
        langchain_msgs: list[BaseMessage] = []
        for msg in messages:
            if msg.role == 'system':
                langchain_msgs.append(SystemMessage(content=msg.content))
            elif msg.role == 'assistant':
                langchain_msgs.append(AIMessage(content=msg.content))
            else:
                langchain_msgs.append(HumanMessage(content=msg.content))
        return langchain_msgs

    async def generate(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY / GEMINI_API_KEY is missing")
            
        lc_messages = self._convert_messages(messages)
        res = await self.llm.ainvoke(lc_messages)
        
        content = res.content if isinstance(res.content, str) else str(res.content)
        usage = 0
        if hasattr(res, 'usage_metadata') and res.usage_metadata:
            usage = res.usage_metadata.get('total_tokens', 0)
            
        return LLMResponse(
            content=content,
            tokens_used=usage,
            model=self.model_name,
            finish_reason='stop'
        )

    async def generate_structured(self, messages: list[Message], response_schema: type[BaseModel], **kwargs: Any) -> BaseModel:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY / GEMINI_API_KEY is missing")
            
        lc_messages = self._convert_messages(messages)
        structured_llm = self.llm.with_structured_output(response_schema)
        res = await structured_llm.ainvoke(lc_messages)
        
        if isinstance(res, response_schema):
            return res
        elif isinstance(res, dict):
            return response_schema.model_validate(res)
        else:
            raise ValueError(f"Unexpected response type from structured LLM: {type(res)}")


def get_llm_provider() -> LLMProvider:
    provider_name = os.environ.get("LLM_PROVIDER", settings.llm_provider)
    if provider_name == 'gemini':
        return GeminiProvider()
    return MockProvider()
