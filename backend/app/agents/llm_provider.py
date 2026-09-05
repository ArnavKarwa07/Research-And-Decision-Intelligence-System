from typing import Literal, Any, Optional, get_origin
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
                origin = get_origin(f.annotation)
                annot = f.annotation
                if annot == str:
                    fields[k] = "mock"
                elif annot == int or annot == float:
                    fields[k] = 0
                elif annot == bool:
                    fields[k] = False
                elif origin is dict or annot == dict:
                    fields[k] = {}
                elif origin is list or annot == list:
                    fields[k] = []
                else:
                    fields[k] = None
            return response_schema(**fields)

class GeminiProvider(LLMProvider):
    """
    Google Gemini provider using ChatGoogleGenerativeAI from langchain_google_genai.
    """
    
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or settings.gemini_api_key
        self.model_name = model_name or settings.gemini_model or "gemini-flash-latest"
        
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found. GeminiProvider will fail if invoked.")
        else:
            logger.info(f"Initialized GeminiProvider with model: {self.model_name}")
            
        from langchain_google_genai import ChatGoogleGenerativeAI
        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            google_api_key=self.api_key,
            temperature=0.2,
            max_retries=1,
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
            raise ValueError("GEMINI_API_KEY is missing")
            
        try:
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
        except Exception as e:
            logger.error(f"Gemini LLM generation error for model '{self.model_name}': {e}", exc_info=True)
            raise RuntimeError(f"Gemini LLM generation failed for model '{self.model_name}': {str(e)}") from e

    async def generate_structured(self, messages: list[Message], response_schema: type[BaseModel], **kwargs: Any) -> BaseModel:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing")
            
        try:
            lc_messages = self._convert_messages(messages)
            structured_llm = self.llm.with_structured_output(response_schema)
            res = await structured_llm.ainvoke(lc_messages)
            
            if isinstance(res, response_schema):
                return res
            elif isinstance(res, dict):
                return response_schema.model_validate(res)
            else:
                raise ValueError(f"Unexpected response type from structured LLM: {type(res)}")
        except Exception as e:
            logger.error(f"Gemini structured LLM generation error for schema {response_schema.__name__} (model '{self.model_name}'): {e}", exc_info=True)
            raise RuntimeError(f"Gemini structured LLM generation failed: {str(e)}") from e


class RotationalGeminiProvider(LLMProvider):
    """
    Rotational Gemini provider that iterates over candidate models on API errors, rate limits, or unsupported model errors.
    """
    CANDIDATE_MODELS = [
        "gemini-flash-latest",
        "gemini-flash-lite-latest",
        "gemini-1.5-flash",
        "gemma-2-27b-it",
        "gemma-2-9b-it",
    ]

    def __init__(self, api_key: str | None = None, candidate_models: list[str] | None = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or settings.gemini_api_key
        self.candidate_models = candidate_models or list(self.CANDIDATE_MODELS)
        self.current_index = 0

    def _is_rotatable_error(self, exc: Exception) -> bool:
        rotatable_types = []
        try:
            from google.api_core.exceptions import (
                GoogleAPICallError, ResourceExhausted, ServiceUnavailable, NotFound, InvalidArgument
            )
            rotatable_types.extend([GoogleAPICallError, ResourceExhausted, ServiceUnavailable, NotFound, InvalidArgument])
        except ImportError:
            pass
        try:
            from urllib.error import HTTPError
            rotatable_types.append(HTTPError)
        except ImportError:
            pass
        try:
            import httpx
            rotatable_types.extend([httpx.HTTPError, httpx.HTTPStatusError])
        except ImportError:
            pass

        if rotatable_types and isinstance(exc, tuple(rotatable_types)):
            return True

        err_msg = str(exc).lower()
        exc_type = type(exc).__name__.lower()
        keywords = [
            "429", "503", "404", "400",
            "resource_exhausted", "quota", "not found", "invalid argument",
            "rate limit", "overloaded"
        ]
        if any(kw in err_msg for kw in keywords) or any(kw in exc_type for kw in keywords):
            return True
        return False

    async def generate(self, messages: list[Message], **kwargs: Any) -> LLMResponse:
        last_error = None
        start_idx = self.current_index
        num_candidates = len(self.candidate_models)

        for attempt in range(num_candidates):
            model_name = self.candidate_models[(start_idx + attempt) % num_candidates]
            provider = GeminiProvider(api_key=self.api_key, model_name=model_name)
            try:
                res = await provider.generate(messages, **kwargs)
                self.current_index = (start_idx + attempt) % num_candidates
                return res
            except Exception as e:
                last_error = e
                if self._is_rotatable_error(e):
                    logger.warning(f"RotationalGeminiProvider encountered rate limit / unavailable error ({e}) on model '{model_name}'. Rotating to next candidate.")
                    continue
                else:
                    raise e

        raise RuntimeError(f"All candidate Gemini models failed after rotation: {last_error}") from last_error

    async def generate_structured(self, messages: list[Message], response_schema: type[BaseModel], **kwargs: Any) -> BaseModel:
        last_error = None
        start_idx = self.current_index
        num_candidates = len(self.candidate_models)

        for attempt in range(num_candidates):
            model_name = self.candidate_models[(start_idx + attempt) % num_candidates]
            provider = GeminiProvider(api_key=self.api_key, model_name=model_name)
            try:
                res = await provider.generate_structured(messages, response_schema, **kwargs)
                self.current_index = (start_idx + attempt) % num_candidates
                return res
            except Exception as e:
                last_error = e
                if self._is_rotatable_error(e):
                    logger.warning(f"RotationalGeminiProvider structured call encountered rate limit / unavailable error ({e}) on model '{model_name}'. Rotating to next candidate.")
                    continue
                else:
                    raise e

        raise RuntimeError(f"All candidate Gemini models failed structured generation after rotation: {last_error}") from last_error


def get_llm_provider() -> LLMProvider:
    provider_name = os.environ.get("LLM_PROVIDER", settings.llm_provider)
    if provider_name == 'gemini':
        return RotationalGeminiProvider()
    return MockProvider()

