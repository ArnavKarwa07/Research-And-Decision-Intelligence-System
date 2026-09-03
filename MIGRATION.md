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

### Anticipated Database Schema Changes (Phase 2)

As we move into Phase 2, the following schema migrations will be necessary:

1. **User Accounts & Authentication:**
   - Introduction of `User` models.
   - Foreign key relations linking `Session` to `User`.
2. **Agent State Persistence:**
   - Transitioning the in-memory message bus to a durable queue (e.g., Redis, RabbitMQ).
   - Adding an `AgentStateLog` table to persist intermediate reasoning steps, allowing paused or interrupted queries to be resumed.
3. **Feedback Loops:**
   - Adding `UserFeedback` tables to link user ratings/corrections directly to specific `Evidence` or `Query` rows for fine-tuning future agent behaviors.

### Breaking Changes & Migration Steps

- **Data Serialization:** Transitioning from lightweight Phase 1 Pydantic schemas to strictly versioned API contracts may require data backfills or schema translations for existing `Session` and `Evidence` data.
- **Message Bus:** Shifting from the Phase 1 in-memory bus to a durable backend will require updating the BaseAgent and SSE streaming endpoints to subscribe to external message brokers. No existing data migration is strictly necessary for this, but runtime infrastructure changes are required.

Always test migrations against a staging clone of the database before applying `alembic upgrade head` in production.
