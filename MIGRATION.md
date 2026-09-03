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
