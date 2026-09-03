# Migration Guide

This document outlines database migration strategies and provides a roadmap for transitioning the Research And Decision Intelligence System (RADIS) from Phase 1 to Phase 2.

## Database Initialization (Phase 1)

In Phase 1, RADIS utilizes **async SQLAlchemy** paired with **Alembic** for schema migrations.

### Alembic Readiness

The backend is fully configured for Alembic migrations. The foundational models (`Session`, `Query`, `Evidence`, `Source`) have been mapped.

To initialize the database locally and apply the first migration:

1. Ensure your database URI is correctly set in `.env` (e.g., SQLite for local dev, PostgreSQL for production).
2. Generate the initial revision (if not already present):
   ```bash
   cd backend
   alembic revision --autogenerate -m "Initial schema: sessions, queries, evidence, sources"
   ```
3. Apply the migration to the database:
   ```bash
   alembic upgrade head
   ```

## Phase 1 to Phase 2 Expansion Path

Phase 1 established the core multi-agent framework, robust tool safety mechanisms, and the real-time SSE-driven UI. Phase 2 will focus on persistence, advanced reasoning capabilities, and scalable infrastructure.

## Phase 2 Implemented Schema Additions

Phase 2 adds durable agent state persistence and multi-agent plan storage to the database:

1. **`AgentRun` Table (`agent_runs`):**
   - Stores sub-agent execution runs linked via `query_id` foreign key (`queries.id`).
   - Fields: `id` (UUID), `query_id` (FK), `agent_type` (String), `status` (String), `steps_taken` (Integer), `tokens_used` (Integer), `elapsed_seconds` (Float), `error` (Text), `execution_log` (JSON).
2. **`Query` Table JSON Extensions (`queries.research_plan`):**
   - Stores the structured sub-task plan array, `decision_matrix`, `audit_passed` flag, and `audit_issues` array directly in `research_plan`.

### Migration Execution

To apply the Phase 2 schema migrations to local SQLite/PostgreSQL:

```bash
cd backend
alembic revision --autogenerate -m "Add agent_runs table and query research_plan json"
alembic upgrade head
```

## Phase 3 Implemented Schema Additions (Evidence Intelligence)

Phase 3 introduces advanced evidence tracking, scoring, and contradiction resolution tables:

1. **New Tables:**
   - `claims`: Stores atomic extracted claims (7-type taxonomy) and confidence scores. Includes columns: `query_id`, `created_by_agent_run_id`, `verified_at`, `metadata`.
   - `claim_sources`: Junction table mapping claims to sources with excerpt and support type.
   - `source_groups`: Groups related sources for independence scoring.
   - `source_group_members`: Junction table mapping sources to groups.
   - `contradictions`: Stores detected conflicts, severity scores, and resolution states. Includes columns: `query_id`, `claim_a_id`, `claim_b_id`, `contradiction_type`, `severity`, `resolution_status`, `resolution_notes`, `metadata`.

2. **`sources` Table Extensions:**
   - Added columns: `publisher`, `source_type`, `published_at`, `content_hash` (indexed for content deduplication lookup), `independence_group`, and `freshness_category`.

### Migration Execution (Phase 3)

To apply the Phase 3 schema migrations to local SQLite/PostgreSQL:

```bash
cd backend
alembic revision --autogenerate -m "Phase 3 Evidence Intelligence additions"
alembic upgrade head
```

## Phase 4 Implemented Schema & Infrastructure Additions (Internal Knowledge + RAG)

Phase 4 introduces internal document parsing, hierarchical semantic chunking, dense vector embeddings, and Qdrant integration.

### 1. Vector Database Container Configuration (`docker-compose.yml`)

Qdrant is configured as a dedicated container service in `docker-compose.yml`:

```yaml
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
```

A named volume `qdrant_data` is configured to persist vector index data across container restarts.

### 2. Database Schema Additions (`Document`, `DocumentChunk`, `VectorCollection`)

Phase 4 adds three core tables mapped via SQLAlchemy models in `app.models.document`:

1. **`documents` Table (`Document` model):**
   - Stores uploaded document records linked to a session (`session_id` FK).
   - Columns: `id` (UUID, PK), `session_id` (FK to `sessions.id`), `filename` (String), `mime_type` (String), `file_path` (String), `file_size` (Integer), `file_hash` (String), `status` (Enum/String: `queued`, `parsing`, `chunking`, `embedding`, `stored`, `failed`), `error_message` (Text), `chunk_count` (Integer), `metadata_json` (JSON), `created_at` (DateTime), `updated_at` (DateTime).

2. **`document_chunks` Table (`DocumentChunk` model):**
   - Stores text chunks extracted from documents with parent-child hierarchical relations.
   - Columns: `id` (UUID, PK), `document_id` (FK to `documents.id`), `chunk_index` (Integer), `content` (Text), `content_hash` (String, indexed), `token_count` (Integer), `page_number` (Integer, nullable), `section_heading` (String, nullable), `start_offset` (Integer), `end_offset` (Integer), `parent_chunk_id` (FK to `document_chunks.id`, self-reference), `embedding_id` (String, nullable), `metadata_json` (JSON), `created_at` (DateTime).

3. **`vector_collections` Table (`VectorCollection` model):**
   - Tracks session vector collections provisioned in Qdrant.
   - Columns: `id` (UUID, PK), `session_id` (FK to `sessions.id`), `name` (String, unique), `dimension` (Integer), `distance_metric` (String, default `cosine`), `chunk_count` (Integer), `created_at` (DateTime).

### 3. Environment Variable Settings

Configure the following environment variables in `.env` or system environment (`app/config.py`):

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `QDRANT_URL` | `http://localhost:6333` | Connection URL for Qdrant REST service |
| `QDRANT_API_KEY` | `None` | Optional API key for authenticated Qdrant instances |
| `EMBEDDING_PROVIDER` | `mock` | Dense embedding provider (`mock`, `openai`, `huggingface`) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Model name for vector embeddings |
| `EMBEDDING_DIMENSION` | `1536` | Embedding vector dimensionality |
| `CHUNK_SIZE` | `512` | Target token limit per document chunk |
| `CHUNK_OVERLAP` | `64` | Token overlap between adjacent chunks |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size limit (in MB) |
| `DOCUMENT_STORAGE_PATH` | `./uploads/documents` | Server disk directory for original uploaded documents |

### Migration Execution (Phase 4)

To apply the Phase 4 schema additions to local SQLite/PostgreSQL:

```bash
cd backend
alembic revision --autogenerate -m "Phase 4 Internal Knowledge + RAG additions"
alembic upgrade head
```

## Phase 5 Implemented Schema & Self-Challenge Additions

Phase 5 introduces autonomous self-challenge engines, competing hypothesis tracking, red-team critique auditing, and dynamic graph re-planning.

### 1. Database Schema Additions (`Hypothesis`, `CritiqueReport`)

Phase 5 adds two new tables mapped via SQLAlchemy models in `app.models.hypothesis` and `app.models.critique_report`:

1. **`hypotheses` Table (`Hypothesis` model):**
   - Stores generated competing hypotheses linked to a research query (`query_id` FK).
   - Columns: `id` (UUID, PK), `query_id` (FK to `queries.id`, `ondelete="CASCADE"`, indexed), `statement` (Text), `status` (String, default `"proposed"`), `confidence` (Float, default `0.5`), `supporting_claim_ids` (JSON), `falsifying_claim_ids` (JSON), `evidence_map` (JSON), `falsification_attempts` (Integer, default `0`), `max_falsification_attempts` (Integer, default `5`), `metadata` (JSON), `created_at` (DateTime), `updated_at` (DateTime).

2. **`critique_reports` Table (`CritiqueReport` model):**
   - Stores independent red-team audit findings and remediation recommendations linked to a query (`query_id` FK).
   - Columns: `id` (UUID, PK), `query_id` (FK to `queries.id`, `ondelete="CASCADE"`, indexed), `synthesis_snapshot` (Text), `findings` (JSON), `weak_evidence` (JSON), `missing_variables` (JSON), `overall_severity` (String, default `"LOW"`), `recommendations` (JSON), `replan_triggered` (Boolean, default `False`), `iteration` (Integer, default `1`), `created_at` (DateTime), `updated_at` (DateTime).

### 2. Environment Variable & Configuration Settings (`app/config.py`)

The following Phase 5 configuration settings are available in `app/config.py` / `.env`:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `MAX_REPLAN_ITERATIONS` | `3` | Maximum dynamic re-planning loop iterations allowed per query |
| `CONFIDENCE_THRESHOLD` | `0.3` | Minimum acceptable confidence threshold before triggering re-planning |
| `HYPOTHESIS_COUNT_LIMIT` | `7` | Maximum number of competing hypotheses generated per research query |
| `CRITIC_STRICTNESS` | `"HIGH"` | Red-team auditing strictness level (`"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"`) |

### 3. Migration Execution (Phase 5)

To apply the Phase 5 schema additions to local SQLite/PostgreSQL:

```bash
cd backend
alembic revision --autogenerate -m "Phase 5 Self-Challenge and Dynamic Re-planning additions"
alembic upgrade head
```

### 4. Backward Compatibility Notes

- **Non-Breaking Schema Extensions**: All new tables (`hypotheses`, `critique_reports`) use Foreign Key references to `queries.id` with `ON DELETE CASCADE`. Existing tables (`sessions`, `queries`, `claims`, `contradictions`, `documents`, `vector_collections`) remain 100% untouched.
- **Optional Relationships**: `Query.hypotheses` and `Query.critique_reports` relationships are defined with `cascade="all, delete-orphan"`, ensuring safe cleanup without affecting existing queries.
- **Graceful Fallbacks**: Queries submitted in Phase 1-4 standard mode continue to execute cleanly without requiring hypothesis generation or red-team critique passes unless explicitly triggered via `/self-challenge` or `/critique` endpoints.

