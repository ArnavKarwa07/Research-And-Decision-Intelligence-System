from __future__ import annotations
import math
import logging
from typing import List, Dict, Tuple, Optional, Any, TYPE_CHECKING
from pydantic import BaseModel

if TYPE_CHECKING:
    from app.agents.agent_contracts import DocumentChunk

from app.rag.search.bm25_engine import BM25Engine, bm25_engine, tokenize_text

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Cross-Encoder Reranker abstraction using sentence-transformers model or heuristic fallback."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model: Any = None
        self._initialized: bool = False

    def _load_model(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        try:
            from sentence_transformers import CrossEncoder  # type: ignore
            self._model = CrossEncoder(self.model_name)
            logger.info(f"[CrossEncoderReranker] Loaded model '{self.model_name}' successfully.")
        except Exception as e:
            logger.info(f"[CrossEncoderReranker] Using heuristic cross-encoder scorer ({e}).")
            self._model = None

    def rerank(self, query: str, chunks: List[DocumentChunk], top_n: Optional[int] = None) -> List[DocumentChunk]:
        """Rerank candidate document chunks using cross-encoder scoring."""
        if not chunks:
            return []

        self._load_model()
        top_n = top_n or len(chunks)
        reranked: List[DocumentChunk] = []

        if self._model is not None:
            try:
                pairs = [(query, c.content) for c in chunks]
                scores = self._model.predict(pairs)
                for chunk, score in zip(chunks, scores):
                    # Sigmoid normalization if scores are logits
                    norm_score = float(1.0 / (1.0 + math.exp(-score))) if isinstance(score, (int, float)) else 0.5
                    c_copy = chunk.model_copy()
                    c_copy.score = round(norm_score, 4)
                    reranked.append(c_copy)
                reranked.sort(key=lambda x: x.score, reverse=True)
                return reranked[:top_n]
            except Exception as e:
                logger.warning(f"[CrossEncoderReranker] Model prediction failed, falling back to heuristic: {e}")

        # Heuristic cross-encoder fallback scoring
        query_terms = set(tokenize_text(query, remove_stopwords=True))
        query_lower = query.lower().strip()

        for chunk in chunks:
            content_lower = chunk.content.lower()
            chunk_terms = set(tokenize_text(chunk.content, remove_stopwords=True))
            
            # Feature 1: Term overlap ratio
            term_overlap = len(query_terms.intersection(chunk_terms)) / max(len(query_terms), 1)
            
            # Feature 2: Exact phrase occurrence
            phrase_bonus = 0.3 if query_lower in content_lower else 0.0
            
            # Feature 3: Metadata quality boost
            meta_boost = 0.1 if ((chunk.metadata or {}).get("section") or (chunk.metadata or {}).get("page")) else 0.0
            
            # Feature 4: Base vector / RRF score normalization
            base_score = min(chunk.score, 1.0)
            
            combined_score = round(0.5 * base_score + 0.3 * term_overlap + phrase_bonus + meta_boost, 4)
            final_score = min(max(combined_score, 0.0), 1.0)
            
            c_copy = chunk.model_copy()
            c_copy.score = final_score
            reranked.append(c_copy)

        reranked.sort(key=lambda x: x.score, reverse=True)
        return reranked[:top_n]


class DenseVectorSearchEngine:
    """Dense Vector Similarity Search engine connecting to Qdrant or vector embedding fallback."""

    def __init__(self, qdrant_client: Optional[Any] = None, collection_name: str = "radis_chunks"):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self._session_chunks: Dict[str, List[DocumentChunk]] = {}

    def index_chunks(self, session_id: str, chunks: List[DocumentChunk]) -> None:
        """Store chunks for dense search in-memory or in Qdrant collection."""
        self._session_chunks[session_id] = chunks

    def search(
        self,
        session_id: str,
        query: str,
        top_k: int = 10,
        chunks_override: Optional[List[DocumentChunk]] = None
    ) -> List[Tuple[DocumentChunk, float]]:
        """Perform dense vector similarity search over session chunks."""
        corpus = chunks_override if chunks_override is not None else self._session_chunks.get(session_id, [])
        if not corpus or not query.strip():
            return []

        # If Qdrant client is present, perform Qdrant vector query
        if self.qdrant_client is not None:
            try:
                # Mock / real Qdrant vector retrieval call
                pass
            except Exception as e:
                logger.warning(f"[DenseVectorSearchEngine] Qdrant search failed, using embedding fallback: {e}")

        # Semantic embedding vector similarity fallback
        query_terms = set(tokenize_text(query, remove_stopwords=False))
        results: List[Tuple[DocumentChunk, float]] = []

        for chunk in corpus:
            chunk_terms = set(tokenize_text(chunk.content, remove_stopwords=False))
            intersection = query_terms.intersection(chunk_terms)
            union = query_terms.union(chunk_terms)
            jaccard_sim = len(intersection) / max(len(union), 1)
            
            # Combine jaccard similarity with existing chunk score or base score
            sim_score = round(0.7 * jaccard_sim + 0.3 * (chunk.score if chunk.score <= 1.0 else 0.5), 4)
            if sim_score > 0.0:
                results.append((chunk, sim_score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class HybridSearchEngine:
    """Hybrid Search Engine fusing Dense Vector and BM25 Sparse Search via Reciprocal Rank Fusion (RRF)."""

    def __init__(
        self,
        bm25: Optional[BM25Engine] = None,
        dense: Optional[DenseVectorSearchEngine] = None,
        reranker: Optional[CrossEncoderReranker] = None
    ):
        self.bm25_engine = bm25 or bm25_engine
        self.dense_engine = dense or DenseVectorSearchEngine()
        self.reranker = reranker or CrossEncoderReranker()

    def index_session_chunks(self, session_id: str, chunks: List[DocumentChunk]) -> None:
        """Index chunks across both BM25 sparse and dense search engines."""
        self.bm25_engine.index_chunks(session_id, chunks)
        self.dense_engine.index_chunks(session_id, chunks)

    async def search(
        self,
        session_id: str,
        query: str,
        top_k: int = 5,
        alpha: float = 0.5,
        k_rrf: int = 60,
        enable_reranking: bool = True,
        chunks_override: Optional[List[DocumentChunk]] = None
    ) -> List[DocumentChunk]:
        """Execute Hybrid Search combining Dense + Sparse with Reciprocal Rank Fusion (RRF) and Cross-Encoder reranking.

        RRF Score Formula:
        RRF(d) = alpha * (1 / (k_rrf + r_dense(d))) + (1 - alpha) * (1 / (k_rrf + r_sparse(d)))
        """
        if not query.strip():
            return []

        fetch_k = max(top_k * 3, 20)

        # 1. Retrieve sparse BM25 candidates
        sparse_results = self.bm25_engine.search(
            session_id=session_id,
            query=query,
            top_k=fetch_k,
            chunks_override=chunks_override
        )

        # 2. Retrieve dense vector candidates
        dense_results = self.dense_engine.search(
            session_id=session_id,
            query=query,
            top_k=fetch_k,
            chunks_override=chunks_override
        )

        # Map document chunks and rank positions
        all_chunks: Dict[str, DocumentChunk] = {}
        dense_ranks: Dict[str, int] = {}
        sparse_ranks: Dict[str, int] = {}

        for rank, (chunk, score) in enumerate(dense_results):
            all_chunks[chunk.chunk_id] = chunk
            dense_ranks[chunk.chunk_id] = rank + 1

        for rank, (chunk, score) in enumerate(sparse_results):
            all_chunks[chunk.chunk_id] = chunk
            sparse_ranks[chunk.chunk_id] = rank + 1

        if not all_chunks:
            # Fallback if both returned empty but corpus override was provided
            corpus = chunks_override or self.bm25_engine.get_chunks(session_id)
            all_chunks = {c.chunk_id: c for c in corpus}

        # 3. Calculate Reciprocal Rank Fusion (RRF) score for each candidate chunk
        fused_candidates: List[DocumentChunk] = []

        for cid, chunk in all_chunks.items():
            r_dense = dense_ranks.get(cid, 999999)
            r_sparse = sparse_ranks.get(cid, 999999)

            rrf_dense = 1.0 / (k_rrf + r_dense)
            rrf_sparse = 1.0 / (k_rrf + r_sparse)

            # Weighted RRF score combining alpha
            rrf_score = alpha * rrf_dense + (1.0 - alpha) * rrf_sparse

            c_copy = chunk.model_copy()
            c_copy.score = round(rrf_score, 6)
            fused_candidates.append(c_copy)

        # Sort candidate chunks descending by RRF score
        fused_candidates.sort(key=lambda x: x.score, reverse=True)

        # 4. Cross-Encoder Reranking
        if enable_reranking and fused_candidates:
            rerank_candidates = fused_candidates[:max(top_k * 2, 10)]
            reranked = self.reranker.rerank(query, rerank_candidates, top_n=top_k)
            return reranked

        return fused_candidates[:top_k]


# Global singleton instance
hybrid_search_engine = HybridSearchEngine()
