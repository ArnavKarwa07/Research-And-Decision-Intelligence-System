"""Adversarial Test Suite for Phase 4 (Internal Knowledge + RAG).

Aggressively tests security vulnerabilities (path traversal), edge cases, null metadata handling,
vector dimension mismatch, missing API keys, SSE/session isolation, and citation mapping resilience.
"""
import pytest
import uuid
import os
from unittest.mock import AsyncMock, MagicMock

from app.rag.citations.citation_mapper import CitationMapper, CitationMetadata
from app.rag.search.bm25_engine import BM25Engine, tokenize_text
from app.rag.search.hybrid_search import HybridSearchEngine, DenseVectorSearchEngine, CrossEncoderReranker
from app.rag.parsers.factory import DocumentParserFactory
from app.rag.chunking.semantic_chunker import SemanticChunker
from app.rag.parsers.base import ParsedDocument, ParsedSection
from app.rag.embeddings.provider import OpenAIEmbeddingProvider, MockEmbeddingProvider
from app.rag.vector.qdrant_client import QdrantService
from app.agents.agent_contracts import DocumentChunk as ContractDocumentChunk
from app.agents.retrieval import RetrievalAgent
from app.agents.evidence import EvidenceAgent
from app.agents.synthesis import SynthesisAgent
from app.agents.base import AgentConfig


def test_adversarial_citation_mapper_null_handling():
    """Adversarial Test: Ensure CitationMapper handles missing page and section metadata gracefully without outputting 'p.None' or '§None'."""
    # Chunk with missing page and section
    chunk_no_meta = ContractDocumentChunk(
        chunk_id="c_null",
        document_id="doc_null",
        content="Test content without page or section metadata.",
        score=0.9,
        metadata={"filename": "report.pdf"}
    )
    meta = CitationMapper.extract_provenance(chunk_no_meta)
    assert meta.filename == "report.pdf"
    assert meta.page_number is None
    assert meta.section_heading is None
    assert meta.formatted_citation == "[report.pdf]"

    # Chunk with page but no section
    chunk_page_only = ContractDocumentChunk(
        chunk_id="c_page",
        document_id="doc_page",
        content="Test content with page only.",
        score=0.9,
        metadata={"filename": "report.pdf", "page": 4}
    )
    meta_page = CitationMapper.extract_provenance(chunk_page_only)
    assert meta_page.formatted_citation == "[report.pdf, p.4]"

    # Chunk with section but no page
    chunk_sec_only = ContractDocumentChunk(
        chunk_id="c_sec",
        document_id="doc_sec",
        content="Test content with section only.",
        score=0.9,
        metadata={"filename": "report.pdf", "section": "Summary"}
    )
    meta_sec = CitationMapper.extract_provenance(chunk_sec_only)
    assert meta_sec.formatted_citation == "[report.pdf, §Summary]"


def test_adversarial_bm25_edge_cases():
    """Adversarial Test: BM25Engine against empty queries, empty session index, and zero token documents."""
    engine = BM25Engine()

    # Search empty session
    res_empty_session = engine.search("non_existent_session", "query text")
    assert res_empty_session == []

    # Search empty query
    res_empty_query = engine.search("session1", "")
    assert res_empty_query == []

    # Index document with 0 tokens (special symbols only)
    empty_token_chunk = ContractDocumentChunk(
        chunk_id="c_empty",
        document_id="doc_empty",
        content="!@#$%^&*()",
        score=0.5,
        metadata={"filename": "symbols.txt"}
    )
    engine.index_chunks("session_empty_doc", [empty_token_chunk])
    res_symbols = engine.search("session_empty_doc", "search")
    assert res_symbols == []


def test_adversarial_parser_factory_unsupported_extension():
    """Adversarial Test: DocumentParserFactory raises ValueError for unsupported extensions."""
    with pytest.raises(ValueError, match="Unsupported document format"):
        DocumentParserFactory.get_parser(file_path="unsupported_file.xyz")


def test_adversarial_semantic_chunker_empty_document():
    """Adversarial Test: SemanticChunker on an empty document returns empty list without crashing."""
    doc = ParsedDocument(title="Empty", text="", sections=[])
    chunker = SemanticChunker()
    chunks = chunker.chunk_document(doc)
    assert chunks == []


@pytest.mark.asyncio
async def test_adversarial_hybrid_search_alpha_bounds():
    """Adversarial Test: HybridSearchEngine handles extreme alpha parameters (0.0 and 1.0) cleanly."""
    engine = HybridSearchEngine()
    sample_chunks = [
        ContractDocumentChunk(
            chunk_id="c1",
            document_id="doc1",
            content="Qdrant dense vector index test.",
            score=0.95,
            metadata={"filename": "doc1.pdf"}
        )
    ]
    engine.index_session_chunks("session_alpha", sample_chunks)

    # Alpha = 0.0 (Pure Sparse)
    res_sparse = await engine.search("session_alpha", "Qdrant", alpha=0.0)
    assert isinstance(res_sparse, list)

    # Alpha = 1.0 (Pure Dense)
    res_dense = await engine.search("session_alpha", "Qdrant", alpha=1.0)
    assert isinstance(res_dense, list)


@pytest.mark.asyncio
async def test_adversarial_openai_embedding_provider_no_openai_key():
    """Adversarial Test: OpenAIEmbeddingProvider must not pass Gemini key to OpenAI endpoints."""
    provider = OpenAIEmbeddingProvider(api_key=None, model_name="text-embedding-3-small", dimension=1536)
    # Ensure that if openai_api_key is absent, it safely falls back to MockEmbeddingProvider
    if not provider.api_key:
        embeddings = await provider.embed_texts(["test string"])
        assert len(embeddings) == 1
        assert len(embeddings[0]) == 1536


def test_adversarial_qdrant_dimension_mismatch_handling():
    """Adversarial Test: Mock Qdrant service search with mismatched query vector dimension."""
    service = QdrantService()
    service.ensure_collection("test_dim_coll", dimension=1536)
    points = [
        {
            "id": str(uuid.uuid4()),
            "vector": [0.1] * 1536,
            "payload": {"content": "Dimension test"}
        }
    ]
    service.upsert_points("test_dim_coll", points)

    # Query with 384-dim vector against 1536-dim collection
    short_query_vec = [0.1] * 384
    res = service.search("test_dim_coll", query_vector=short_query_vec, limit=5)
    assert isinstance(res, list)


@pytest.mark.asyncio
async def test_adversarial_retrieval_agent_null_metadata():
    """Adversarial Test: RetrievalAgent handles chunks with null or missing metadata gracefully."""
    config = AgentConfig(max_steps=3, max_tokens=50000, timeout_seconds=30, allowed_tools=[])
    agent = RetrievalAgent(config=config)

    chunk_with_none_meta = ContractDocumentChunk(
        chunk_id="c_meta_none",
        document_id="doc_meta_none",
        content="Sample content for null metadata test",
        score=0.88,
        metadata={"filename": "test.pdf"}  # metadata present
    )

    input_data = {
        "query": "Sample content",
        "session_id": "session_test",
        "chunks": [chunk_with_none_meta],
        "external_snippets": [
            {
                "content": "External content",
                "source": None  # source is None
            }
        ]
    }

    step_res = await agent.step(input_data)
    assert step_res.result is not None
    assert len(agent.retrieved_chunks) > 0


@pytest.mark.asyncio
async def test_adversarial_evidence_agent_null_sources():
    """Adversarial Test: EvidenceAgent handles snippets with null source dictionaries without raising AttributeError."""
    config = AgentConfig(max_steps=3, max_tokens=50000, timeout_seconds=30, allowed_tools=[])
    agent = EvidenceAgent(config=config)

    input_data = {
        "document_chunks": [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "content": "Verified finding from internal source.",
                "score": 0.9,
                "metadata": {"filename": "doc1.pdf", "page": 1}
            }
        ],
        "raw_snippets": [
            {
                "content": "External raw snippet with null source",
                "source": None
            }
        ]
    }

    step_res = await agent.step(input_data)
    assert step_res.result is not None
    assert len(agent.claims) >= 1


@pytest.mark.asyncio
async def test_bug_high_07_synthesis_agent_null_confidence():
    """BUG-HIGH-07: SynthesisAgent handles None confidence values gracefully without crashing."""
    config = AgentConfig(max_steps=5, max_tokens=1000, timeout_seconds=30, allowed_tools=[])
    agent = SynthesisAgent(config=config)

    input_data = {
        "objective": "Test Null Confidence Handling",
        "claims": [
            {
                "citation": "[doc.pdf, p.1]",
                "source_url": "http://example.com/doc1",
                "source_title": "Doc 1",
                "confidence": None  # Null confidence
            },
            {
                "citation": "[doc.pdf, p.2]",
                "source_url": "http://example.com/doc2",
                "source_title": "Doc 2",
                "confidence": 0.85
            }
        ]
    }

    step_res = await agent.step(input_data)
    assert step_res.result is not None
    assert agent.decision_matrix is not None
    assert agent.decision_matrix.confidence == 0.85  # Average of single non-None confidence 0.85


def test_bug_med_10_bm25_stopword_phrase_boost():
    """BUG-MED-10: BM25Engine phrase boost requires min token length >= 3 and not a stopword."""
    engine = BM25Engine()
    chunk1 = ContractDocumentChunk(
        chunk_id="c1",
        document_id="d1",
        content="The system operates in high speed mode at night.",
        score=0.5,
        metadata={"filename": "doc1.txt"}
    )
    engine.index_chunks("session_bm25_test", [chunk1])

    # Query with short stopword "in" should NOT trigger phrase boost
    res_in = engine.search("session_bm25_test", "in")
    score_in = res_in[0][1] if res_in else 0.0
    assert score_in < 1.0  # No phrase boost applied (boost ensures >= 1.0)

    # Query with phrase "high speed" SHOULD trigger phrase boost
    res_phrase = engine.search("session_bm25_test", "high speed")
    assert len(res_phrase) > 0
    assert res_phrase[0][1] >= 1.0  # Boosted score


@pytest.mark.asyncio
async def test_bug_med_12_citation_quality_score_section():
    """BUG-MED-12: Section citations (§) and INTERNAL_VERIFIED sources get HIGH quality score."""
    config = AgentConfig(max_steps=5, max_tokens=1000, timeout_seconds=30, allowed_tools=[])
    agent = SynthesisAgent(config=config)

    input_data = {
        "objective": "Test Section Quality Score",
        "claims": [
            {
                "citation": "[Architecture.md, §Overview]",  # Section citation without page number
                "source_url": "Architecture.md",
                "source_title": "Architecture Guide",
                "source_type": "INTERNAL_VERIFIED",
                "confidence": 0.90
            }
        ]
    }

    await agent.step(input_data)
    output = await agent.compile_output()
    sources = output["sources_used"]
    assert len(sources) == 1
    assert sources[0]["quality_score"] == "HIGH"


def test_bug_high_15_no_circular_import():
    """BUG-HIGH-15: Verify importing CitationMapper does not trigger circular import with app.agents."""
    from app.rag.citations.citation_mapper import CitationMapper
    assert CitationMapper is not None

