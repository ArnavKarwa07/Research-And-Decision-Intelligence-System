# TRD.md

# Technical Requirements Document

## 1. Technical Objective

Build an extensible agentic runtime that can autonomously plan, execute, evaluate, and revise multi-step research and decision tasks while preserving durable task state, provenance, observability, and safety controls.

## 2. High-Level Architecture

```text
Web / Mobile Browser
        |
     React.js UI
        |
   API Gateway / Auth
        |
      FastAPI
        |
 Task / Run Service
        |
 Agent Orchestrator
        |
 +------+---------+------------------+
 |      |         |                  |
Research Data  Evidence          Decision
Agents   Agents Agent            Agents
 |      |         |                  |
 +------+---------+------------------+
        |
      Tool Layer
        |
 +------+-----+------+-------+------+
 |            |      |       |      |
Web        SQL     RAG     Python  APIs
Search      DB    Search  Sandbox
        |
  Data / Knowledge Layer
        |
Postgres | Qdrant | Object Storage | Redis
        |
Telemetry / Evals / Audit
```

## 3. Reference Stack

### Frontend

- React.js
- TypeScript
- Tailwind CSS
- Component library
- SSE or WebSocket run updates

### Backend

- Python 3.12+
- FastAPI
- Pydantic
- AsyncIO

### Agent Runtime

- LangGraph or a custom state-machine/orchestration layer
- Structured tool schemas
- Durable state checkpoints
- Explicit agent budgets

### Storage

- PostgreSQL for transactional state, users, projects, tasks, runs, claims, sources, decisions
- Qdrant for vector retrieval
- S3-compatible object storage for files and artifacts
- Redis for caching, locks, rate limiting, short-lived state

### Async Execution

- Redis queue initially or Celery
- Kafka when event streaming and scale require it

### Observability

- OpenTelemetry
- Langfuse/Phoenix-compatible tracing
- Prometheus
- Grafana

### Deployment

- Docker
- GitHub Actions
- AWS or equivalent cloud
- Kubernetes after service boundaries stabilize

## 4. Core Domain Model

### User

Identity, preferences, permissions.

### Project

Long-lived workspace containing research, files, decisions, and knowledge.

### Task

User-level objective with status, mode, budget, constraints, and desired output.

### Run

One execution instance of a task.

### AgentRun

Execution of one agent within a run.

### ToolCall

An invocation of a tool by an agent.

### Source

External or internal information source with metadata.

### Claim

Atomic factual assertion extracted from a source, user input, tool result, or agent output.

### EvidenceLink

Relationship between a claim and one or more evidence items.

### Assumption

Explicit assumption used by the system or user.

### Hypothesis

Potential explanation or decision hypothesis under investigation.

### Decision

Recommendation plus alternatives, criteria, uncertainty, assumptions, and supporting evidence.

### Evaluation

Quality assessment of a run, agent trajectory, claim, tool call, or final answer.

## 5. Agent State

Agent state must be machine-readable and durable.

```python
class ResearchState:
    task_id: str
    objective: str
    constraints: list[str]
    decision_criteria: list[str]
    hypotheses: list[str]
    sub_tasks: list[dict]
    claims: list[dict]
    sources: list[dict]
    evidence_links: list[dict]
    contradictions: list[dict]
    assumptions: list[dict]
    pending_questions: list[str]
    completed_actions: list[dict]
    failed_actions: list[dict]
    confidence: float | None
    budget_remaining: dict
    next_action: str | None
```

## 6. Agent Contract

Every agent must define:

- Purpose
- Inputs
- Outputs
- Allowed tools
- Preconditions
- Stop conditions
- Failure conditions
- Budget limits
- Confidence semantics
- Escalation conditions

Agents must return structured output wherever possible.

## 7. Core Agents

### Supervisor / Orchestrator

Owns task decomposition, routing, state transitions, budgets, and completion criteria.

### Research Agent

Finds and extracts relevant information from external sources.

### Retrieval Agent

Searches internal project knowledge and documents.

### Evidence Agent

Maps claims to evidence and rates support quality.

### Fact Check Agent

Independently verifies specific claims.

### Data Analyst Agent

Uses SQL/Python/statistics to investigate structured data.

### Contradiction Agent

Identifies and resolves conflicting evidence.

### Hypothesis Agent

Generates and investigates alternative explanations.

### Critic / Red-Team Agent

Attempts to falsify preliminary conclusions.

### Decision Agent

Compares alternatives and produces recommendations under uncertainty.

### Synthesis Agent

Produces the user-facing result with citations, assumptions, uncertainty, and next steps.

## 8. Dynamic Orchestration

The orchestrator must support:

- Parallel branches
- Sequential dependencies
- Conditional branching
- Agent spawning
- Retry with alternate tool
- Re-planning
- Human approval gates
- Early termination
- Budget-aware execution
- Checkpoint/resume

The orchestration graph must not require all tasks to follow the same sequence.

## 9. Tool Layer

Tools are capabilities, not agents.

### Research tools

- web_search
- browse_url
- extract_page
- news_search
- academic_search

### Knowledge tools

- semantic_search
- keyword_search
- hybrid_search
- retrieve_document

### Data tools

- query_sql
- inspect_schema
- run_python
- load_csv
- load_excel

### Decision tools

- compare_options
- run_scenario
- run_sensitivity
- calculate_expected_value

### Artifact tools

- create_report
- create_chart
- export_evidence_table

## 10. Tool Security

Each tool requires:

- Auth policy
- Input validation
- Permission scope
- Timeout
- Retry policy
- Audit logging
- Cost classification

Dangerous tools require user approval.

## 11. RAG Requirements

Support:

- File ingestion
- Text extraction
- Metadata extraction
- Chunking
- Embedding
- Vector indexing
- Keyword retrieval
- Hybrid search
- Metadata filtering
- Reranking
- Parent/child context
- Citation mapping

Document chunks must preserve document ID, page/section, source URI, and content offsets when available.

## 12. Evidence Model

Every material claim should have one of:

- Direct source support
- Calculation support
- User-provided support
- Model inference
- Unsupported / unresolved

Claim confidence must not be identical to model confidence. Confidence should account for evidence quality and independence.

## 13. Agentic Loop

```text
INTAKE
  -> PLAN
  -> EXECUTE
  -> COLLECT EVIDENCE
  -> VALIDATE
  -> DETECT GAPS
  -> CHALLENGE
  -> RE-PLAN
  -> SYNTHESIZE
```

Re-planning occurs when any stop criterion fails.

## 14. Stop Conditions

Stop when one or more of the following is true:

- Completion criteria satisfied
- Evidence coverage threshold reached
- Additional research has low expected value
- Budget exhausted
- Time limit reached
- User decision required
- Safety policy requires escalation

## 15. API Requirements

Minimum APIs:

```text
POST   /projects
GET    /projects/{id}
POST   /projects/{id}/tasks
GET    /tasks/{id}
POST   /tasks/{id}/runs
GET    /runs/{id}
GET    /runs/{id}/events
GET    /runs/{id}/sources
GET    /runs/{id}/claims
GET    /runs/{id}/decisions
POST   /runs/{id}/approve
POST   /runs/{id}/cancel
POST   /documents
POST   /search
```

## 16. Event Model

Run events should support:

```text
run.started
plan.created
agent.started
agent.updated
tool.started
tool.completed
tool.failed
claim.created
source.created
contradiction.detected
research.replanned
human.approval_required
run.completed
run.failed
```

## 17. Reliability Requirements

- Idempotent task/run creation
- Retryable tool execution
- Durable checkpoints
- Dead-letter handling for failed background tasks
- Timeouts on all remote calls
- Backpressure for expensive research
- Circuit breakers for unstable providers

## 18. Performance Targets

Initial targets:

- Chat interaction acknowledgement < 500 ms where possible
- Tool event visible to UI < 1 s after emission
- P95 quick-answer latency < 8 s
- Deep research jobs asynchronous
- 99.5% monthly API availability target for production phase

## 19. Cost Controls

Each run has:

- Token budget
- Search budget
- Tool budget
- Time budget
- Agent-depth limit

The orchestrator must track estimated and actual cost.

## 20. Deployment Topology

MVP can run as:

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

Later split into independent services only where scale or ownership justifies it.

## 21. CI/CD

Required checks:

- Unit tests
- Type checks
- Linting
- Integration tests
- Agent contract tests
- Prompt/eval regression tests
- Container build
- Security scan

## 22. Environment Management

Separate:

- local
- test
- staging
- production

Secrets must be stored outside source control.
