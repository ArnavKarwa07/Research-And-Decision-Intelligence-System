# Developer Guide

Welcome to the Research And Decision Intelligence System (RADIS) developer documentation. This guide provides an overview of the architecture, setup instructions, and engineering rules.

## Architecture Overview

RADIS is structured as a monorepo containing a Python backend and a pure JavaScript Vite + React frontend styled 1-to-1 with the Stitch MCP Design System.

- **Backend (`/backend`)**: Built with FastAPI and Python 3.12. It handles database interactions via async SQLAlchemy (supporting SQLite for local dev & PostgreSQL for production), orchestrates multi-agent workflows using a custom `BaseAgent` framework with an extended LangGraph conditional routing state machine (`should_reverify`), manages LLM interactions, and exposes REST endpoints and Server-Sent Events (SSE) streams.
- **Frontend (`/frontend`)**: A pure JavaScript React application powered by Vite (running natively on **port 5173**). Rebuilt to align 1-to-1 with the Stitch MCP UI Prototype (`RADIS Decision Command Center`). Styled with Tailwind CSS, Google Material Symbols, micro-caps typography, radar hero animations, live telemetry stream timelines, and zero non-functional buttons or dummy fallbacks. Audited with `react-doctor` (**100/100 Great score**).

## Quickstart Guide

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm
- Docker & Docker Compose (optional, for containerized deployments)

### Backend Setup
1. Navigate to the backend directory: `cd backend`
2. Create a virtual environment: `python -m venv .venv`
3. Activate the environment:
   - Windows: `.\.venv\Scripts\activate`
   - Unix/macOS: `source .venv/bin/activate`
4. Install dependencies: `pip install -e ".[dev]"`
5. Copy `.env.example` to `.env` and configure optional LLM/Search API keys.

### Frontend Setup
1. Navigate to the frontend directory: `cd frontend`
2. Install dependencies: `npm install`
3. Configure `VITE_API_URL=http://localhost:8000/api/v1` if using a custom backend port.

## Running Locally

**Start the Backend (Development mode)**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
Backend API will be accessible at `http://localhost:8000`. Health check: `http://localhost:8000/health`.

**Start the Frontend (Development mode)**
```bash
cd frontend
npm run dev
```
The application will be accessible on Vite's native dev port: **`http://localhost:5173`**.

## No Non-Functional UI / No Dummy Data Policy

The codebase enforces a strict **Zero Non-Functional UI & Zero Dummy Data** policy:
- **Pruned Placeholder UI**: All non-functional links, dummy tabs, and dead buttons have been removed. Every visible element performs a real action (creating sessions, submitting queries, switching research modes, opening live terminal telemetry logs, copying evidence, or exporting PDF reports).
- **Web Search**: Integrates live DuckDuckGo HTML web search (`_duckduckgo_search`) in `backend/app/tools/web_search.py` so real searches run out-of-the-box without requiring API keys or mock data.
- **Real Error Handling**: Network or backend exceptions display real error banners with interactive retry triggers.

## Agent Engineering Rules

RADIS employs a strict set of rules for agent development to ensure reliability, predictability, and safety:

1. **Strict Budgeting:** All agents must enforce token limits, step limits, and timeout budgets (`asyncio.wait_for`). Runaway loops are strictly prohibited.
2. **Immutable State:** Agent state transitions must be predictable and auditable. State is passed and returned, not mutated globally.
3. **Graceful Degradation:** When APIs fail or timeouts approach, agents must yield real partial results or clear error states rather than crashing or inventing fake facts.
4. **Tool Safety:** All tools must be registered via the central registry with input schema validation. Content extractors enforce strict SSRF protections (`is_safe_url`).
5. **Separation of Concerns:** The Supervisor Agent plans and delegates; Research Agents execute and gather. Never mix orchestration with execution.
6. **Streaming First:** Intermediate progress and evidence emit via SSE to drive real-time UI.
7. **Phase 3 Evidence Intelligence Pipeline:**
   - **`ClaimExtractor` & `ConfidenceEngine`**: Extracts atomic claims into a 7-type taxonomy and scores them via weighted formulas.
   - **`SourceScorer`**: Assesses credibility, freshness, and independence of sources.
   - **`FactCheckAgent`**: Uses 3 search strategies (Direct, Authority, Counter-evidence) and enforces strict URL/`content_hash` deduplication.
   - **`ContradictionAgent`**: Runs a 5-check detection pipeline for conflicts, assigns severity scores, and drives a resolution state machine.
   - **`ProvenanceAgent`**: Builds the Evidence Graph engine.
   - **LangGraph Routing (`should_reverify`)**: Routes execution to additional verification loops if confidence is low or contradictions are severe.

## Phase 4 RAG Pipeline Architecture & Extensibility

Phase 4 equips RADIS with an internal document processing engine, vector database storage, and hybrid retrieval algorithms.

### 1. RAG Pipeline Architecture

```
[Uploaded Document] 
      │
      ▼
┌───────────────────────────┐
│  DocumentParserFactory    │ ── (Parses PDF, DOCX, TXT, Markdown)
└─────────────┬─────────────┘
              │ Extract raw text & section metadata
              ▼
┌───────────────────────────┐
│   SemanticChunker         │ ── (Parent-Child Hierarchical Chunking)
└─────────────┬─────────────┘
              │ Chunks & hierarchy
              ▼
┌───────────────────────────┐
│     EmbeddingService      │ ── (Generates dense vector embeddings)
└─────────────┬─────────────┘
              │ 
      ┌───────┴────────┐
      ▼                ▼
┌───────────┐    ┌───────────┐
│  Qdrant   │    │  BM25     │
│ (Dense)   │    │ (Sparse)  │
└─────┬─────┘    └─────┬─────┘
              │                │
              └───────┬────────┘
                      ▼
┌───────────────────────────┐
│ Reciprocal Rank Fusion    │ ── (RRF combining Dense + Sparse search)
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│  Cross-Encoder Reranker   │ ── (Multi-stage precision score elevation)
└─────────────┬─────────────┘
              ▼
┌───────────────────────────┐
│     CitationMapper        │ ── (Source Attribution: [Doc: name, Page: X])
└───────────────────────────┘
```

The key modules in `app/rag` perform:
1. **Multi-Format Document Parsing (`app/rag/parsers`)**: Selects appropriate parser via `DocumentParserFactory` based on MIME type or file extension.
2. **Hierarchical Semantic Chunking (`app/rag/chunking`)**: `SemanticChunker` splits document content into macro parent chunks and granular child chunks, preserving section headings, page numbers, and offsets.
3. **Qdrant Vector Store (`app/rag/vector`)**: `QdrantClientManager` handles collection provisioning, vector upserts with payload metadata, payload filtering by session ID, and collection cleanup.
4. **BM25 Keyword Engine (`app/rag/search/bm25_engine.py`)**: Computes sparse BM25 scores over chunk corpora for exact lexical and keyword matches.
5. **Hybrid Search & RRF (`app/rag/search/hybrid_search.py`, `rrf.py`)**: Combines dense Qdrant vector scores and sparse BM25 keyword scores using Reciprocal Rank Fusion (RRF) parameterized by `alpha`.
6. **Cross-Encoder Reranking (`app/rag/search/reranker.py`)**: Rescores candidate chunks against search query using cross-encoder scoring.
7. **Citation Mapping (`app/rag/citations/citation_mapper.py`)**: Attaches structured citation references (`[Doc: filename, Page: X, Chunk: Y]`) to chunk payloads injected into LLM context windows.

### 2. Parser Factory Extensibility Guide

To add support for a new document format (e.g. `CSVParser` or `HTMLParser`):

1. **Implement `BaseDocumentParser` Subclass**:
   Create a new file in `app/rag/parsers/my_parser.py`:
   ```python
   from app.rag.parsers.base import BaseDocumentParser, ParsedDocument

   class MyCustomParser(BaseDocumentParser):
       async def parse(self, file_path: str) -> ParsedDocument:
           # Extract text content, page divisions, sections, and metadata
           return ParsedDocument(
               content="Extracted full document text...",
               metadata={"format": "custom"},
               pages=[{"page_number": 1, "text": "..."}],
               sections=[{"title": "Header", "start_offset": 0}]
           )
   ```

2. **Register Parser in `DocumentParserFactory`**:
   Update `app/rag/parsers/factory.py`:
   ```python
   _MIME_MAP: dict[str, Type[BaseDocumentParser]] = {
       ...
       "application/x-custom": MyCustomParser,
   }

   _EXTENSION_MAP: dict[str, Type[BaseDocumentParser]] = {
       ...
       ".custom": MyCustomParser,
   }
   ```

3. **Add Tests**:
   Add unit tests in `tests/unit/test_phase4_rag.py` to verify factory registration, text extraction, and metadata assignment.

### 3. Instructions for Running Qdrant Locally

**Option 1: Docker Compose (Recommended)**
Start Qdrant container alongside PostgreSQL and Redis:
```bash
docker-compose up -d qdrant
```
- REST API: `http://localhost:6333`
- Web Dashboard: `http://localhost:6333/dashboard`
- gRPC Port: `6334`

**Option 2: Standalone Docker Container**
```bash
docker run -d -p 6333:6333 -p 6334:6334 \
    -v qdrant_data:/qdrant/storage \
    --name radis-qdrant \
    qdrant/qdrant:latest
```

**Checking Service Status:**
```bash
curl http://localhost:6333/healthz
```
Expected response: `{"title":"qdrant","status":"ok"}`.

## Testing & Audit Commands

**Backend:**
- Module imports check: `python -c "import app.models; import app.schemas; import app.agents; import app.tools; import app.services; import app.api.v1.router"`
- Ruff Linter: `ruff check app`
- Type checking: `mypy app`

**Frontend:**
- Vite Production Build: `npm run build`
- React Doctor Quality Audit: `npx react-doctor .` (Audited: **100/100 Great score**)
