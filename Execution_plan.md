# Execution_plan.md

# Phased Execution Plan

Each phase contains **no more than two primary features**. The phases are ordered so every stage produces a usable system and prepares the architecture for the next stage.

## Phase 0 - Foundation

### Feature 1: Repository & Runtime Foundation

Build:

- Monorepo structure
- Python backend
- React.js frontend
- Shared schemas
- Environment management
- Docker Compose
- Basic CI

### Feature 2: Core Domain Model

Implement:

- User
- Project
- Task
- Run
- Source
- Claim
- AgentRun
- Decision

**Exit criteria:** app starts locally, database migrations work, authenticated user can create a project and task.

---

## Phase 1 - MVP Interaction

### Feature 1: Conversational Task Intake

Build:

- Chat interface
- Task creation
- Objective extraction
- Basic clarifying questions
- Run state

### Feature 2: Single-Agent Research MVP

Build:

- Initial research agent
- Web search tool
- Source collection
- Citation-aware answer

**Exit criteria:** user can ask a research question and receive a cited answer with persistent run history.

---

## Phase 2 - Agentic Core

### Feature 1: Dynamic Planner / Orchestrator

Build:

- Task decomposition
- Structured research plan
- Dependencies
- Parallel branches
- Agent selection
- Durable state

### Feature 2: Multi-Agent Execution

Build:

- Research agent
- Retrieval agent
- Evidence agent
- Synthesis agent
- Agent contracts

**Exit criteria:** the system chooses multiple agents dynamically and stores their execution state.

---

## Phase 3 - Evidence Intelligence

### Feature 1: Claim & Evidence Graph

Build:

- Atomic claims
- Evidence links
- Provenance
- Source metadata
- Claim confidence

### Feature 2: Fact Check & Contradiction Detection

Build:

- Independent verification
- Contradiction agent
- Outdated-source detection
- Unresolved conflict states

**Exit criteria:** final answers distinguish supported, contradicted, inferred, and unresolved claims.

---

## Phase 4 - Internal Knowledge + RAG

### Feature 1: Document Ingestion & Knowledge Base

Build:

- PDF/DOCX ingestion
- Object storage
- Metadata extraction
- Chunking
- Embeddings
- Qdrant

### Feature 2: Hybrid Retrieval

Build:

- Semantic search
- BM25/keyword search
- Hybrid retrieval
- Reranking
- Citation mapping

**Exit criteria:** research can combine external web evidence with user-provided internal documents.

---

## Phase 5 - Self-Challenge

### Feature 1: Alternative Hypothesis Engine

Build:

- Hypothesis generation
- Hypothesis tracking
- Evidence per hypothesis
- Falsification tasks

### Feature 2: Critic / Red-Team Loop

Build:

- Independent critique
- Weak evidence detection
- Missing-variable detection
- Re-planning trigger

**Exit criteria:** the system can challenge and revise its own preliminary conclusion.

---

## Phase 6 - Decision Intelligence

### Feature 1: Decision Framework

Build:

- Alternatives
- Criteria
- Weighted scoring
- Risks
- Recommendation
- Confidence

### Feature 2: Scenario & Sensitivity Analysis

Build:

- Best/base/worst cases
- Sensitivity analysis
- Expected value
- Decision triggers

**Exit criteria:** system can move from research to quantified decision support.

---

## Phase 7 - Data Agent

### Feature 1: Data Investigation Agent

Build:

- SQL tool
- Schema inspection
- CSV/Excel handling
- Python analysis
- Statistical functions

### Feature 2: Data Visualization

Build:

- Chart generation
- Table generation
- Embedded findings
- Reproducible analysis artifacts

**Exit criteria:** user can ask why a business metric changed and receive data-backed analysis.

---

## Phase 8 - Human-in-the-Loop + Safety

### Feature 1: Approval & Clarification Gates

Build:

- User questions
- Approval gates
- Evidence correction
- Assumption confirmation

### Feature 2: Tool Security

Build:

- Tool permission scopes
- Prompt injection defense
- PII handling
- Sandboxed Python
- Audit logs

**Exit criteria:** dangerous or ambiguous actions are gated safely.

---

## Phase 9 - Production Agent Runtime

### Feature 1: Long-Running Research Jobs

Build:

- Worker execution
- Queues
- Checkpoint/resume
- Retry policies
- Failure recovery

### Feature 2: Agent Budgets & Cost Controls

Build:

- Token budget
- Search budget
- Tool budget
- Time budget
- Agent depth limits

**Exit criteria:** deep research survives failures and cannot run uncontrolled.

---

## Phase 10 - LLMOps & Evaluation

### Feature 1: Evaluation Framework

Build:

- Golden datasets
- Retrieval metrics
- Claim verification
- Citation evaluation
- Agent trajectory evaluation
- Decision quality evaluation

### Feature 2: Observability

Build:

- Traces
- Logs
- Metrics
- Token/cost monitoring
- Agent timeline
- Regression dashboards

**Exit criteria:** every major change can be evaluated against known quality and cost baselines.

---

## Phase 11 - Production UX

### Feature 1: Research Workspace

Build:

- Plan view
- Evidence view
- Decision view
- Agent activity
- Sources
- Claims

### Feature 2: Artifact Generation

Build:

- Decision memo
- Research report
- Comparison table
- Export package

**Exit criteria:** the product feels like a research workspace rather than a chat application.

---

## Phase 12 - Continuous Intelligence

### Feature 1: Research Monitoring

Build:

- Scheduled re-research
- Baseline comparison
- Change detection
- Materiality scoring

### Feature 2: Persistent Project Memory

Build:

- Decision history
- Prior conclusions
- Lessons from past research
- Reusable assumptions

**Exit criteria:** the system can keep decisions current rather than only answer one-off questions.

---

## Phase 13 - Enterprise Expansion

### Feature 1: Enterprise Connectors

Build progressively:

- Google Drive
- Notion
- Slack
- Gmail
- SharePoint

### Feature 2: Collaboration & Governance

Build:

- RBAC
- Team projects
- SSO
- Audit history
- Admin controls

**Exit criteria:** multi-user deployment is feasible for controlled organizations.

---

# Development Rule

Do not start the next phase until the current phase has:

- Automated tests for its core behavior
- Observable failure modes
- Documented APIs/contracts
- A small evaluation set
- A usable end-to-end demo
