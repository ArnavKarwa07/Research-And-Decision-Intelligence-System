"""Unit and Integration tests for Phase 4 RAG (P4-01 through P4-08)."""
import os
import tempfile
import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.models.base import Base
from app.models.session import Session
from app.models.document import Document, DocumentChunk, VectorCollection
from app.rag.parsers.factory import DocumentParserFactory
from app.rag.parsers.txt_parser import TXTParser
from app.rag.parsers.markdown_parser import MarkdownParser
from app.rag.chunking.semantic_chunker import SemanticChunker
from app.rag.embeddings.provider import MockEmbeddingProvider, get_embedding_provider
from app.rag.vector.qdrant_client import QdrantService


@pytest.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        
    await engine.dispose()


@pytest.mark.asyncio
async def test_document_models(test_db: AsyncSession):
    """Test P4-02: Document, DocumentChunk, VectorCollection models."""
    session_obj = Session(id=uuid.uuid4(), title="RAG Test Session")
    test_db.add(session_obj)
    await test_db.commit()

    doc = Document(
        id=uuid.uuid4(),
        session_id=session_obj.id,
        filename="test_report.pdf",
        mime_type="application/pdf",
        file_path="/tmp/test_report.pdf",
        file_size=1024,
        file_hash="dummyhash123",
        status="queued",
    )
    test_db.add(doc)
    await test_db.commit()

    chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc.id,
        chunk_index=0,
        content="This is chunk content for RAG testing.",
        content_hash="chunkhash123",
        token_count=8,
        page_number=1,
        section_heading="Introduction",
    )
    test_db.add(chunk)

    vec_coll = VectorCollection(
        id=uuid.uuid4(),
        session_id=session_obj.id,
        name=f"session_{session_obj.id.hex}",
        dimension=1536,
        distance_metric="cosine",
        chunk_count=1,
    )
    test_db.add(vec_coll)
    await test_db.commit()

    assert doc.id is not None
    assert doc.status == "queued"
    assert chunk.document_id == doc.id
    assert vec_coll.dimension == 1536


def test_document_parsers():
    """Test P4-04: Document parser factory, TXT and Markdown parsers."""
    # Test TXT Parser
    with tempfile.NamedTemporaryFile("w+", suffix=".txt", delete=False) as f:
        f.write("Line 1: Sample text.\n\nLine 2: Paragraph 2.")
        txt_path = f.name

    try:
        parser = DocumentParserFactory.get_parser(file_path=txt_path)
        assert isinstance(parser, TXTParser)
        parsed = parser.parse(txt_path)
        assert len(parsed.sections) == 2
        assert "Sample text" in parsed.text
    finally:
        os.remove(txt_path)

    # Test Markdown Parser
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write("# Introduction\nWelcome to RAG system.\n\n## Architecture\nThis is hierarchical chunking.")
        md_path = f.name

    try:
        parser = DocumentParserFactory.get_parser(file_path=md_path)
        assert isinstance(parser, MarkdownParser)
        parsed = parser.parse(md_path)
        assert len(parsed.sections) == 2
        assert parsed.sections[0].heading == "Introduction"
        assert parsed.sections[1].heading == "Architecture"
    finally:
        os.remove(md_path)


def test_semantic_chunker():
    """Test P4-05: Parent-Child Hierarchical Semantic Chunker."""
    from app.rag.parsers.base import ParsedDocument, ParsedSection

    doc = ParsedDocument(
        title="Test Document",
        text="Sample full text",
        sections=[
            ParsedSection(
                heading="Overview",
                text="This is a long introductory section " + ("about intelligence systems " * 50),
                page_number=1,
            )
        ]
    )

    chunker = SemanticChunker(chunk_size=64, chunk_overlap=16, parent_chunk_size=128)
    chunks = chunker.chunk_document(doc)

    assert len(chunks) > 0
    parent_chunks = [c for c in chunks if c.parent_chunk_index is None]
    child_chunks = [c for c in chunks if c.parent_chunk_index is not None]

    assert len(parent_chunks) > 0
    assert len(child_chunks) > 0
    for child in child_chunks:
        assert child.parent_chunk_index in [p.chunk_index for p in parent_chunks]


@pytest.mark.asyncio
async def test_embedding_provider():
    """Test P4-06: Mock Embedding Provider producing 1536-dim unit vectors."""
    provider = get_embedding_provider("mock")
    assert isinstance(provider, MockEmbeddingProvider)

    texts = ["Research Intelligence System", "Vector Database Qdrant"]
    embeddings = await provider.embed_texts(texts)

    assert len(embeddings) == 2
    assert len(embeddings[0]) == 1536
    assert len(embeddings[1]) == 1536


def test_qdrant_service_mock():
    """Test P4-06: Qdrant service collection management and search fallback."""
    q_service = QdrantService(url="http://invalid-host:6333")
    coll_name = "test_collection"

    assert q_service.ensure_collection(collection_name=coll_name, dimension=1536)

    pt_id = str(uuid.uuid4())
    points = [
        {
            "id": pt_id,
            "vector": [0.1] * 1536,
            "payload": {"content": "Sample Qdrant content", "doc_id": "123"},
        }
    ]

    assert q_service.upsert_points(coll_name, points)

    results = q_service.search(coll_name, query_vector=[0.1] * 1536, limit=5)
    assert len(results) == 1
    assert results[0]["payload"]["doc_id"] == "123"

    assert q_service.delete_points(coll_name, [pt_id])
    assert len(q_service.search(coll_name, query_vector=[0.1] * 1536)) == 0


# --- Phase 4-09 through P4-13 Tests ---
from app.agents.base import AgentConfig
from app.agents.agent_contracts import DocumentChunk as ContractDocumentChunk
from app.rag.search.bm25_engine import BM25Engine, BM25SessionIndex, tokenize_text
from app.rag.search.hybrid_search import HybridSearchEngine, CrossEncoderReranker
from app.rag.citations.citation_mapper import CitationMapper
from app.agents.retrieval import RetrievalAgent
from app.agents.evidence import EvidenceAgent
from app.agents.synthesis import SynthesisAgent



@pytest.fixture
def rag_sample_chunks():
    return [
        ContractDocumentChunk(
            chunk_id="c1",
            document_id="doc1",
            content="RADIS architecture uses a lexical BM25 sparse search engine for keywords.",
            score=0.9,
            metadata={"filename": "architecture.pdf", "page": 1, "section": "Search"}
        ),
        ContractDocumentChunk(
            chunk_id="c2",
            document_id="doc1",
            content="Dense vector similarity search uses Qdrant for semantic embeddings.",
            score=0.85,
            metadata={"filename": "architecture.pdf", "page": 2, "section": "Vector Store"}
        ),
        ContractDocumentChunk(
            chunk_id="c3",
            document_id="doc2",
            content="Reciprocal Rank Fusion RRF fuses dense and sparse results with k=60.",
            score=0.8,
            metadata={"filename": "rrf_fusion.md", "page": 5, "section": "RRF Math"}
        ),
    ]


def test_p4_09_bm25_search_engine(rag_sample_chunks):
    """Test P4-09: BM25 Sparse Search Engine tokenization, stop-word removal, exact phrase matching."""
    tokens = tokenize_text("The RADIS system is fast and reliable!")
    assert "the" not in tokens
    assert "and" not in tokens
    assert "radis" in tokens

    engine = BM25Engine(k1=1.5, b=0.75)
    engine.index_chunks("session-p4", rag_sample_chunks)
    
    results = engine.search("session-p4", "BM25 keyword search", top_k=2)
    assert len(results) > 0
    top_chunk, score = results[0]
    assert top_chunk.chunk_id == "c1"
    assert score > 0.0


@pytest.mark.asyncio
async def test_p4_10_hybrid_search_rrf(rag_sample_chunks):
    """Test P4-10: Hybrid Search Engine combining Dense + BM25 with RRF (k=60) and CrossEncoder reranker."""
    engine = HybridSearchEngine()
    engine.index_session_chunks("session-p4", rag_sample_chunks)
    
    results = await engine.search(
        session_id="session-p4",
        query="semantic embeddings and RRF fusion",
        top_k=2,
        alpha=0.5,
        enable_reranking=True
    )
    assert len(results) <= 2
    assert all(isinstance(c, ContractDocumentChunk) for c in results)


def test_p4_13_citation_mapper(rag_sample_chunks):
    """Test P4-13: Provenance citation extraction and formatting."""
    chunk = rag_sample_chunks[0]
    meta = CitationMapper.extract_provenance(chunk)
    assert meta.filename == "architecture.pdf"
    assert meta.page_number == 1
    assert meta.section_heading == "Search"
    assert meta.formatted_citation == "[architecture.pdf, p.1, §Search]"


@pytest.mark.asyncio
async def test_p4_12_retrieval_agent(rag_sample_chunks):
    """Test P4-12: RetrievalAgent hybrid search integration and Source Priority rules."""
    config = AgentConfig(max_steps=5, max_tokens=1000, timeout_seconds=30, allowed_tools=[])
    agent = RetrievalAgent(config)
    
    step_res = await agent.step({
        "query": "BM25 search architecture",
        "session_id": "session-p4",
        "chunks": rag_sample_chunks,
        "external_snippets": [
            {
                "content": "External blog post on search engines.",
                "source": {"url": "https://blog.example.com", "title": "Blog", "qualityScore": "LOW"}
            }
        ]
    })
    
    assert step_res.action == "hybrid_search"
    assert len(agent.retrieved_chunks) > 0
    top_chunk = agent.retrieved_chunks[0]
    assert top_chunk.metadata.get("source_type") == "INTERNAL_VERIFIED"


@pytest.mark.asyncio
async def test_p4_13_agent_citations_pipeline(rag_sample_chunks):
    """Test P4-13: EvidenceAgent and SynthesisAgent end-to-end citation mapping pipeline."""
    config = AgentConfig(max_steps=5, max_tokens=1000, timeout_seconds=30, allowed_tools=[])
    evidence_agent = EvidenceAgent(config)

    
    ev_step = await evidence_agent.step({"document_chunks": rag_sample_chunks})
    claims = ev_step.result
    assert len(claims) > 0
    assert "citation" in claims[0]
    assert claims[0]["citation"].startswith("[")
    
    synthesis_agent = SynthesisAgent(config)
    synth_step = await synthesis_agent.step({
        "objective": "Evaluate Search Architecture",
        "claims": claims
    })
    assert synth_step.action == "synthesize_decision"
    output = await synthesis_agent.compile_output()
    assert output["decision_matrix"] is not None
    assert len(output["sources_used"]) > 0

