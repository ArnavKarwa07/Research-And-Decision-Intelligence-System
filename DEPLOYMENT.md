# DEPLOYMENT.md

# Deployment & Operations

## 1. MVP Deployment

Start with one deployable backend and one worker process.

```text
React.js
FastAPI
Worker
Postgres
Redis
Qdrant
Object Storage
Observability
```

Docker Compose is sufficient for local development.

## 2. Production Evolution

Move to containers with managed:

- PostgreSQL
- Redis
- Object storage
- Vector DB

Use Kubernetes only when workload scale or operational requirements justify it.

## 3. Background Processing

Deep research should execute asynchronously.

Use a durable queue and checkpoint state so a run can resume after worker failure.

## 4. Deployment Pipeline

```text
Git push
  ↓
Lint / Type Check
  ↓
Unit Tests
  ↓
Integration Tests
  ↓
Security Scan
  ↓
Agent Eval Regression
  ↓
Build Container
  ↓
Deploy Staging
  ↓
Smoke Tests
  ↓
Production
```

## 5. Configuration

Separate application configuration from secrets.

Example configuration:

```text
LLM_PROVIDER
LLM_MODEL
EMBEDDING_MODEL
RERANKER_MODEL
DATABASE_URL
REDIS_URL
VECTOR_DB_URL
OBJECT_STORAGE_BUCKET
WEB_SEARCH_PROVIDER
MAX_RUN_COST
MAX_RUN_SECONDS
MAX_AGENT_DEPTH
```

Secrets must come from a managed secret store in production.

## 6. Observability

Monitor:

- Request latency
- Queue depth
- Worker health
- Agent failures
- Tool failures
- Tokens
- Cost
- Retrieval quality
- Evaluation scores
- Error rates

## 7. Alerts

Trigger alerts for:

- API availability degradation
- Queue backlog
- Tool provider outage
- Unexpected cost increase
- High agent loop depth
- Increased citation failures
- Security incidents

## 8. Disaster Recovery

Back up:

- PostgreSQL
- Research artifacts
- Configuration
- Evaluation datasets

Vector indices should be rebuildable from canonical documents and embeddings.

## 9. Rollback

Application deployments must support rapid rollback.

Prompt, model, retriever, and ranking changes must be versioned independently enough to identify regressions.
