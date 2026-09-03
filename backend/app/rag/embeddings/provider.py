from abc import ABC, abstractmethod
import hashlib
import random
import math
from typing import Any
import httpx


from app.config import settings


class BaseEmbeddingProvider(ABC):
    """Abstract base class for vector embedding providers."""

    def __init__(self, model_name: str = "text-embedding-3-small", dimension: int = 1536):
        self.model_name = model_name
        self.dimension = dimension

    @abstractmethod
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of text strings."""
        pass

    async def embed_query(self, text: str) -> list[float]:
        """Generate vector embedding for a single search query."""
        results = await self.embed_texts([text])
        return results[0]


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Mock embedding provider that produces deterministic unit-norm vectors.
    
    Used for local development, offline testing, and CI when no API keys are set.
    """

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            # Create a deterministic seed from the text hash
            hash_digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(hash_digest[:4], "big")
            rng = random.Random(seed)
            
            # Generate random normal vector and normalize to unit length
            vec = [rng.gauss(0, 1) for _ in range(self.dimension)]
            norm = math.sqrt(sum(x * x for x in vec))
            if norm > 0:
                vec = [x / norm for x in vec]
            embeddings.append(vec)
        return embeddings



class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI Embedding API provider using httpx."""

    def __init__(self, api_key: str | None = None, model_name: str = "text-embedding-3-small", dimension: int = 1536):
        super().__init__(model_name=model_name, dimension=dimension)
        self.api_key = api_key or getattr(settings, "openai_api_key", None)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            # Fallback to Mock if no key provided
            mock = MockEmbeddingProvider(model_name=self.model_name, dimension=self.dimension)
            return await mock.embed_texts(texts)

        url = "https://api.openai.com/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": texts,
            "model": self.model_name,
            "dimensions": self.dimension,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # Extract embeddings sorted by index
                data_sorted = sorted(data["data"], key=lambda x: x["index"])
                return [item["embedding"] for item in data_sorted]
        except Exception:
            # Fallback to Mock if key is invalid or API call fails
            mock = MockEmbeddingProvider(model_name=self.model_name, dimension=self.dimension)
            return await mock.embed_texts(texts)


class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    """HuggingFace sentence-transformers local or API embedding provider."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimension: int = 384):
        super().__init__(model_name=model_name, dimension=dimension)
        self._st_model = None

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            from sentence_transformers import SentenceTransformer
            if self._st_model is None:
                self._st_model = SentenceTransformer(self.model_name)
            embeddings = self._st_model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()
        except Exception:
            # Fallback to mock embedding provider
            mock = MockEmbeddingProvider(model_name=self.model_name, dimension=self.dimension)
            return await mock.embed_texts(texts)


def get_embedding_provider(provider_type: str | None = None) -> BaseEmbeddingProvider:
    """Factory function returning the configured embedding provider.

    Args:
        provider_type: 'openai', 'huggingface', or 'mock'. Defaults to settings.embedding_provider.
    """
    p_type = (provider_type or getattr(settings, "embedding_provider", "mock")).lower()
    dim = getattr(settings, "embedding_dimension", 1536)
    model = getattr(settings, "embedding_model", "text-embedding-3-small")

    if p_type == "openai":
        return OpenAIEmbeddingProvider(model_name=model, dimension=dim)
    elif p_type in ("huggingface", "hf"):
        return HuggingFaceEmbeddingProvider(model_name="all-MiniLM-L6-v2", dimension=384)
    else:
        return MockEmbeddingProvider(model_name=model, dimension=dim)
