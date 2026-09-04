# Migration Guide

This document outlines database migration strategies and provides a roadmap for transitioning the Research And Decision Intelligence System (RADIS) from Phase 1 to Phase 9.

## Phase 9 Implemented Production Agent Runtime & Checkpointing Architecture

Phase 9 introduces the Production Agent Runtime featuring async worker pool management, step-level state checkpointing and restoration, multi-dimension budget controls, and real-time SSE cost telemetry.

### 1. Storage & Persistence Architecture

Phase 9 utilizes existing database schemas while extending execution state tracking through `AgentRun` ORM model (`app.models.agent_run`):

1. **`AgentRun.execution_log` (JSON Field Storage):**
   - **`checkpoints` Array**: Stores serialized `Checkpoint` snapshots (`checkpoint_id`, `run_id`, `step_name`, `step_index`, `state`, `claims`, `sources`, `agent_outputs`, `timestamp`).
   - **`latest_checkpoint_id` String**: References the most recent valid step checkpoint identifier.
   - **`budget_stats` Object**: Stores multi-dimension budget usage statistics (`tokens`, `searches`, `tools`, `wall_clock`).
2. **`AgentRun` Existing Column Synchronizations:**
   - `tokens_used`: Automatically updated with total prompt + completion token usage across all steps.
   - `elapsed_seconds`: Automatically updated with total wall-clock duration in seconds.

### 2. Environment Configuration Settings (`app/config.py`)

The following Phase 9 configuration variables govern background worker execution pool and default multi-dimension budget limits:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `WORKER_POOL_CONCURRENCY` | `4` | Maximum concurrent worker tasks in `AsyncWorkerPool` |
| `DEFAULT_MAX_TOKENS` | `100000` | Default hard token limit per research run |
| `DEFAULT_MAX_SEARCHES` | `20` | Default hard search query limit per research run |
| `DEFAULT_MAX_TOOL_CALLS` | `50` | Default hard aggregate tool execution limit per research run |
| `DEFAULT_MAX_WALL_CLOCK_SECONDS` | `300.0` | Default hard wall-clock execution limit (5 minutes) |
| `DEFAULT_SOFT_LIMIT_RATIO` | `0.8` | Warning threshold ratio for soft budget alerts (80%) |

### 3. State Resumption & Backward Compatibility

- **Zero-Downtime Migration**: Phase 9 requires **no raw DB migration scripts** or schema breaking changes. All checkpoint and budget telemetry state is stored cleanly inside existing JSON `execution_log` payloads.
- **Graceful Run Resumption**: When calling `/api/v1/runtime/runs/{id}/resume` or `resume_run_from_checkpoint`, the engine retrieves the latest checkpoint from `CheckpointEngine` memory or falls back to `AgentRun.execution_log["checkpoints"]` DB storage to reconstruct complete typed `AgentState`.
- **Backward Compatibility**: Pre-Phase 9 queries and agent runs function without modification. Uncheckpointed runs default to standard execution state without interruption.

## Phase 8 Implemented Schema & Safety Additions (Human-in-the-Loop & Tool Security)

Phase 8 introduces 3 new database tables for human approval gate management, interactive clarification questions, 5-minute auto-kill timeout tracking, user evidence/assumption overrides, and immutable security audit logging:

1. **`approval_gates` Table (`ApprovalGate` model in `app.models.approval_gate`):**
   - Tracks human approval gates required prior to executing high-risk agent tools (`python_sandbox`, `execute_sql_query`).
   - Columns:
     - `id`: String(36) UUID (Primary Key)
     - `run_id`: String(36) (Foreign Key reference/index, non-null)
     - `agent_id`: String(100) (Agent identifier, non-null)
     - `tool_name`: String(100) (Target tool requested, non-null)
     - `tool_args`: JSON (Sanitized tool argument parameters)
     - `risk_level`: String(20) (Default `"high"`; enum: `low`, `medium`, `high`, `critical`)
     - `description`: Text (Human-readable description of requested action)
     - `status`: String(20) (Indexed; default `"pending"`; enum: `pending`, `approved`, `rejected`, `expired`)
     - `user_feedback`: Text (Nullable; operator feedback or auto-kill message)
     - `timeout_seconds`: Integer (Default `300` seconds / 5 minutes)
     - `created_at`: DateTime (UTC timestamp)
     - `resolved_at`: DateTime (Nullable; UTC timestamp when approved/rejected/expired)

2. **`clarification_questions` Table (`ClarificationQuestion` model in `app.models.clarification`):**
   - Stores interactive clarification questions emitted by agents to resolve task ambiguity.
   - Columns:
     - `id`: String(36) UUID (Primary Key)
     - `run_id`: String(36) (Foreign Key reference/index, non-null)
     - `agent_id`: String(100) (Agent identifier, non-null)
     - `prompt`: Text (Clarification question prompt string)
     - `options`: JSON (Nullable; list of suggested response choices)
     - `answer`: Text (Nullable; user response string or auto-kill notice)
     - `status`: String(20) (Indexed; default `"pending"`; enum: `pending`, `answered`, `expired`)
     - `created_at`: DateTime (UTC timestamp)
     - `resolved_at`: DateTime (Nullable; UTC timestamp when answered/expired)

3. **`audit_logs` Table (`AuditLog` model in `app.models.audit_log`):**
   - Provides immutable audit trail for security events, tool calls, approval gates, PII redactions, and prompt injection attempts.
   - Columns:
     - `id`: String(36) UUID (Primary Key)
     - `run_id`: String(36) (Indexed, nullable)
     - `agent_id`: String(100) (Indexed, nullable)
     - `action_type`: String(100) (Indexed; e.g. `approval_requested`, `approval_auto_killed_timeout`, `prompt_injection_detected`)
     - `severity`: String(20) (Indexed; default `"INFO"`; enum: `INFO`, `WARNING`, `ERROR`, `CRITICAL`)
     - `details`: JSON (Sanitized details object with auto-redacted PII)
     - `timestamp`: DateTime (Indexed UTC timestamp)

### Migration Execution (Phase 8)

To apply Phase 8 schema migrations to local SQLite/PostgreSQL:

```bash
cd backend
alembic revision --autogenerate -m "Phase 8 HITL and Tool Security additions: approval_gates, clarification_questions, audit_logs"
alembic upgrade head
```

### Backward Compatibility & Isolation

- **Non-Breaking Additions**: All Phase 8 tables (`approval_gates`, `clarification_questions`, `audit_logs`) are decoupled standalone tables. Existing tables (`sessions`, `queries`, `claims`, `contradictions`, `documents`, `hypotheses`, `critique_reports`, `decisions`, `data_query_records`) remain 100% untouched.
- **Graceful Fallbacks**: Workflows executing in automated backend modes operate without blocking unless high-risk tools or ambiguous prompts trigger approval or clarification requests.

## Phase 7 Database Schema Additions (Data Agent & Visualization)

Phase 7 introduces 4 new tables for data analysis, structured dataset ingestion, SQL/Python query execution logs, visualization specifications, and reproducible execution artifacts:

- **`uploaded_datasets`**: Stores metadata, column types, row counts, and summary statistics for ingested CSV/XLSX files.
- **`data_query_records`**: Logs SQL and Python sandbox query executions, row counts, and execution timings.
- **`visualization_specs`**: Persists generated Vega-Lite JSON visualization specifications, formatted summary tables, and statistical key findings.
- **`reproducible_artifacts`**: Bundles SQL queries, Python scripts, chart configs, and execution logs into reproducible analysis artifacts.

To apply Phase 7 schema migrations:
```bash
cd backend
alembic revision --autogenerate -m "Add Phase 7 tables: uploaded_datasets, data_query_records, visualization_specs, reproducible_artifacts"
alembic upgrade head
```

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

## Phase 6 Implemented Schema & Decision Intelligence Additions

Phase 6 introduces quantified decision support, multi-criteria decision matrices, best/base/worst scenario modeling, weight sensitivity stress-testing, expected value calculations, and decision triggers.

### 1. Database Schema Additions (`Decision`)

Phase 6 adds a dedicated `decisions` table mapped via SQLAlchemy model in `app.models.decision`:

1. **`decisions` Table (`Decision` model):**
   - Stores structured decision evaluation matrices, scenarios, sensitivity tipping points, and triggers linked to a research query (`query_id` FK).
   - Columns: `id` (UUID, PK), `query_id` (FK to `queries.id`, `ondelete="CASCADE"`, indexed), `recommendation` (Text), `confidence` (Float), `rationale` (Text, nullable), `alternatives` (JSON), `criteria` (JSON), `weighted_matrix` (JSON), `scenarios` (JSON), `sensitivity_analysis` (JSON), `expected_values` (JSON), `key_risks` (JSON), `assumptions` (JSON), `decision_triggers` (JSON), `metadata` (JSON), `created_at` (DateTime), `updated_at` (DateTime).

### 2. Migration Execution (Phase 6)

To apply the Phase 6 schema additions to local SQLite/PostgreSQL:

```bash
cd backend
alembic revision --autogenerate -m "Phase 6 Decision Intelligence additions"
alembic upgrade head
```

### 3. Backward Compatibility Notes

- **Non-Breaking Schema Extensions**: The `decisions` table references `queries.id` with `ON DELETE CASCADE`. Existing tables remain 100% untouched.
- **Optional Relationship**: `Query.decisions` relationship is defined with `cascade="all, delete-orphan"`.


