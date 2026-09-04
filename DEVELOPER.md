# Developer Guide

Welcome to the Research And Decision Intelligence System (RADIS) developer documentation. This guide provides an overview of the architecture, setup instructions, and engineering rules.

## Architecture Overview

RADIS is structured as a monorepo containing a Python backend and a pure JavaScript Vite + React frontend styled 1-to-1 with the Stitch MCP Design System.

- **Backend (`/backend`)**: Built with FastAPI and Python 3.12. It handles database interactions via async SQLAlchemy (supporting SQLite for local dev & PostgreSQL for production), orchestrates multi-agent workflows using a custom `BaseAgent` framework with an extended LangGraph conditional routing state machine (`should_reverify`, `should_replan`, `data_node`, `visualization_node`), manages LLM interactions, sandboxed Python code execution (`PythonSandboxTool`), safe SQL query inspection (`SQLTool`), CSV/Excel data profiling (`CSVTool`), chart spec generation (`ChartTool`), and exposes REST endpoints and SSE streams.
- **Frontend (`/frontend`)**: A pure JavaScript React application powered by Vite (running natively on **port 5173**). Features interactive data visualization card (`DataVisualizationCard.jsx`) and reproducible execution artifacts inspector modal (`DataArtifactsModal.jsx`).


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

## Phase 5 Self-Challenge & Dynamic Re-planning Architecture

Phase 5 introduces autonomous self-challenge mechanisms: competing hypothesis generation, active falsification audits, independent red-team critique, and dynamic graph re-planning.

### 1. Self-Challenge Architecture & Workflow

```mermaid
flowchart TD
    A["Synthesis Snapshot / Preliminary Findings"] --> B["HypothesisAgent"]
    B -->|"Generates 3-7 Competing Hypotheses"| C["hypotheses Table"]
    C --> D["FalsificationAgent"]
    D -->|"Targeted Counter-Queries & Net-Weight Formula"| E["Updated Confidence & Evidence Map"]
    E --> F["CriticAgent (Red-Team)"]
    F -->|"Audit Evidence Quality, Coherence, Omissions, Bias"| G["critique_reports Table"]
    G --> H{"Severity >= HIGH?"}
    H -->|"Yes & Iterations < Max"| I["Dynamic Re-planning Loop"]
    I -->|"Inject remediation sub-tasks"| J["Research & Fact-Check Nodes"]
    J --> A
    H -->|"No or Max Iterations Reached"| K["Final Synthesis with Calibrated Confidence & Caveats"]
```

### 2. Phase 5 Specialist Agents & Contracts

All Phase 5 agents inherit from `BaseAgent` and strictly enforce Pydantic V2 input/output contracts (`app/agents/agent_contracts.py`):

1. **`HypothesisAgent` (`app/agents/hypothesis.py`)**:
   - **Purpose**: Decomposes a research query into 3–7 competing, falsifiable hypothesis items (Primary, Alternative, Null).
   - **Contract**:
     - Input: `HypothesisAgentInput(query_text: str, existing_claims: List[Dict], existing_sources: List[Dict])`
     - Output: `HypothesisAgentOutput(hypotheses: List[HypothesisItem], investigation_priorities: List[str])`
   - **Key Fields**: `statement`, `initial_confidence` (0.5), `discriminating_evidence_needed`.

2. **`FalsificationAgent` (`app/agents/falsification.py`)**:
   - **Purpose**: Formulates targeted disconfirming search queries (`"evidence disproving or refuting: ..."`), retrieves potential counter-evidence, and calculates net-weight updated confidence.
   - **Contract**:
     - Input: `FalsificationInput(hypothesis: HypothesisItem, research_context: str)`
     - Output: `FalsificationOutput(hypothesis_id: str, evidence_items: List[Dict], updated_confidence: float, status_summary: str)`
   - **Confidence Formula**:
     $$\text{Net Weight Ratio} = \frac{\sum W_{\text{supports}} - \sum W_{\text{falsifies}}}{\sum W_{\text{supports}} + \sum W_{\text{falsifies}}}$$
     Mapped linearly from $[-1, 1]$ to $[0, 1]$ and bounded to $[0.0, 1.0]$.

3. **`CriticAgent` (`app/agents/critic.py`)**:
   - **Purpose**: Independent red-team review auditing findings across 4 distinct dimensions without shared state during audit:
     1. *Evidence Quality*: Single-source dependencies, low confidence ($< 0.60$), unverified status.
     2. *Logical Coherence*: Reasoning validity and unstated assumptions.
     3. *Completeness*: Omitted variables (e.g., `financial_cost`, `regulatory_compliance`, `risk_mitigation`).
     4. *Bias Detection*: Confirmation bias ($100\%$ supported claims) and framing bias.
   - **Contract**:
     - Input: `CriticInput(synthesis: str, evidence_chain: List[Dict], hypotheses: List[HypothesisItem], claims: List[Dict])`
     - Output: `CriticOutput(findings: List[str], weak_evidence: List[Dict], missing_variables: List[Dict], overall_severity: str, recommendations: List[str], replan_recommended: bool)`

### 3. Database Table Schemas

Phase 5 adds two primary database entities mapped via SQLAlchemy in `app.models.hypothesis` and `app.models.critique_report`:

1. **`hypotheses` Table (`Hypothesis` model)**:
   - `id`: UUID (PK, default `uuid4`)
   - `query_id`: UUID (FK to `queries.id`, `ondelete="CASCADE"`, indexed)
   - `statement`: Text (Non-null)
   - `status`: String (Default `"proposed"`; enum: `proposed`, `active`, `supported`, `falsified`, `inconclusive`)
   - `confidence`: Float (Default `0.5`)
   - `supporting_claim_ids`: JSON (List of claim UUIDs)
   - `falsifying_claim_ids`: JSON (List of claim UUIDs)
   - `evidence_map`: JSON (List of `EvidenceMapItem` dicts)
   - `falsification_attempts`: Integer (Default `0`)
   - `max_falsification_attempts`: Integer (Default `5`)
   - `metadata`: JSON (Additional metadata such as discriminating evidence lists)
   - `created_at`, `updated_at`: TimestampMixin

2. **`critique_reports` Table (`CritiqueReport` model)**:
   - `id`: UUID (PK, default `uuid4`)
   - `query_id`: UUID (FK to `queries.id`, `ondelete="CASCADE"`, indexed)
   - `synthesis_snapshot`: Text (Non-null)
   - `findings`: JSON (List of finding string summaries)
   - `weak_evidence`: JSON (List of `WeakEvidenceItem` dicts)
   - `missing_variables`: JSON (List of `MissingVariableItem` dicts)
   - `overall_severity`: String (Default `"LOW"`; enum: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
   - `recommendations`: JSON (List of actionable remediation recommendations)
   - `replan_triggered`: Boolean (Default `False`)
   - `iteration`: Integer (Default `1`)
   - `created_at`, `updated_at`: TimestampMixin

### 4. Dynamic Re-planning Workflow & Loop Controls

The LangGraph orchestration engine (`app/agents/graph.py`) incorporates a dynamic feedback loop:

1. **Evaluation**: Following `SynthesisAgent` and `CriticAgent` execution, the `should_replan` conditional edge evaluates the red-team critique report.
2. **Trigger Condition**: If `overall_severity` is rated `HIGH` or `CRITICAL` (or `replan_recommended == True`) and current loop count is below `max_replan_iterations` (default `3`), `replan_triggered` is set to `True`.
3. **Task Injection**: The loop-back action dynamically injects targeted research sub-tasks derived from `remediation` and `missing_variables` recommendations directly back into the `ResearchAgent` and `FactCheckAgent` queues.
4. **Safety & Termination**:
   - Loop iterations are strictly bounded by `max_replan_iterations`.
   - If iteration limit is reached while severity remains elevated, the system finalizes synthesis marked with `finalized_with_caveats = True` and explicit risk warnings.

## Phase 6 Decision Intelligence Architecture

Phase 6 introduces quantified decision support, multi-criteria decision analysis (MCDA), best/base/worst scenario modeling, weight sensitivity stress-testing, expected value calculations, and decision tripwire triggers.

### 1. Decision Intelligence Engine & Tools

Key modules in `app/tools/decision_tools.py` perform pure-Python, deterministic decision calculations:
1. **`compare_options`**: Multi-attribute utility matrix engine. Normalizes criteria weights ($\sum w_j = 1.0$), validates raw scores in $[0.0, 1.0]$, computes weighted total $S_i = \sum w_j \times s_{ij}$, and ranks alternatives.
2. **`run_scenario`**: Evaluates options across Best-case (25%), Base-case (50%), and Worst-case (25%) scenarios with probability distribution normalization.
3. **`run_sensitivity`**: Sweeps criterion weights from 0.0 to 1.0 in `step_size` increments while re-normalizing other criteria proportionally. Identifies exact crossover/switch points where top recommendation flips.
4. **`calculate_expected_value`**: Computes probabilistic expected payoff $EV_i = \sum p_k \times v_{ik}$ across scenarios.

### 2. Decision Agent & Service Architecture

1. **`DecisionAgent` (`app/agents/decision.py`)**: Specialist agent extending `BaseAgent`. Executes multi-criteria scoring, scenario simulation, sensitivity stress-testing, expected value calculation, and decision trigger identification.
2. **`DecisionService` (`app/services/decision_service.py`)**: Manages decision CRUD operations, orchestrates agent execution, persists structured decision records to the database, and executes custom sensitivity/scenario re-runs.

### 3. Database Table (`decisions`)

The `decisions` table (`app/models/decision.py`) tracks:
- `recommendation` & `confidence`
- `alternatives` & `criteria` JSON lists
- `weighted_matrix` JSON
- `scenarios` & `sensitivity_analysis` JSON
- `expected_values` & `decision_triggers` JSON
- Foreign key `query_id` referencing `queries.id` with `ON DELETE CASCADE`.

## Phase 8 Human-in-the-Loop & Safety Framework Architecture

Phase 8 introduces a comprehensive Human-in-the-Loop (HITL) and Security & Safety Framework that governs tool permissions, enforces approval gates, redacts PII, defends against indirect prompt injections, and logs immutable security audit events.

```mermaid
flowchart TD
    A["Agent Tool Call / User Query"] --> B["GatekeeperAgent & SafetyAgent"]
    B -->|"Tool Permission Check"| C{"Requires Approval?"}
    C -->|"Yes (python_sandbox, execute_sql_query)"| D["HITL Approval Gate (pending)"]
    D -->|"5-min (300s) Timeout Check"| E{"Operator Responded?"}
    E -->|"Approved"| F["Execute Tool Safely"]
    E -->|"Rejected / Auto-Killed Timeout"| G["Transition to EXPIRED / REJECTED & Log Audit Event"]
    C -->|"No"| F
    B -->|"Untrusted Retrieval Input"| H["Indirect Prompt Injection Scanner"]
    H -->|"Neutralize patterns & Wrap XML"| I["<untrusted_content> Encapsulated Context"]
    B -->|"Input / Output Data Stream"| J["PII Redaction Engine (Regex + Dict keys)"]
    J -->|"Redact Emails, Tokens, Passwords"| K["Sanitized Audit Log & Agent Context"]
```

### 1. Approval Gates & 5-Minute Auto-Kill Timeouts

- **Mechanism**: High-risk tool calls (such as code execution in `python_sandbox` or direct database mutations in `execute_sql_query`) trigger an `ApprovalGate` entry managed by `HITLService.create_approval_gate`.
- **Status Lifecycle**: Gates move from `pending` to `approved`, `rejected`, or `expired`.
- **5-Minute Auto-Kill Timeout**: To prevent agent execution threads from deadlocking when human operators are offline, `HITLService.check_and_apply_timeouts` checks all pending gates. Any gate older than `timeout_seconds` (default: **300 seconds / 5 minutes**) is automatically transitioned to `EXPIRED` status with user feedback `"Auto-killed by 5-minute timeout."` and an `approval_auto_killed_timeout` audit log event with `ERROR` severity.

### 2. Interactive Clarification Questions

- **Ambiguity Detection**: `GatekeeperAgent` analyzes incoming user query objectives for ambiguity keywords (e.g. `"do whatever"`, `"any option"`, `"choose for me"`, or character length $< 10$).
- **Question & Options Flow**: When ambiguity is detected, `HITLService.create_clarification_question` generates a `ClarificationQuestion` containing a prompt and optional multiple-choice selection options.
- **Timeout Management**: Pending clarification questions also enforce the 5-minute (300s) auto-kill timeout, ensuring workflow execution gracefully terminates or falls back if unanswered.

### 3. Role-Based Tool Permission Scoping

Agent roles are restricted via the `DEFAULT_ROLE_PERMISSIONS` matrix in `app/services/security_service.py`:

| Agent Role | Allowed Tools | Denied Tools | Requires Approval |
| :--- | :--- | :--- | :--- |
| `research` | `web_search`, `content_extractor`, `summarize` | `python_sandbox`, `execute_sql_query` | None |
| `data_agent` | `sql_schema_inspect`, `csv_inspect`, `chart_generate` | `web_search` | `python_sandbox`, `execute_sql_query` |
| `supervisor` | `web_search`, `content_extractor`, `summarize`, `sql_schema_inspect`, `csv_inspect`, `chart_generate` | None | `python_sandbox`, `execute_sql_query` |

Permissions are evaluated dynamically at runtime using `SecurityService.check_tool_permission(agent_role, tool_name)`.

### 4. PII Detection & Redaction Engine

- **Pattern Scanners**: `PII_PATTERNS` regex rules scan for sensitive data formats:
  - `EMAIL`: Standard email pattern
  - `PHONE`: International & US telephone numbers
  - `SSN`: US Social Security Numbers (`\d{3}-\d{2}-\d{4}`)
  - `API_TOKEN` & `BEARER_TOKEN`: Secret tokens and auth headers
  - `PASSWORD_PARAM`: Key/value password parameters
- **Recursive Scanning**: `SecurityService.scan_and_redact_pii(data)` recursively traverses strings, dictionaries, and arrays. Dict keys matching `password`, `secret`, `token`, or `api_key` are replaced with `[REDACTED_SECRET]`.
- **Pre-Persistence Scrubbing**: All audit logs, tool arguments, and SSE log events undergo automatic PII scrubbing before database writes or client transmission.

### 5. Indirect Prompt Injection Defense

- **Attack Vector**: Untrusted web pages or parsed document chunks may contain malicious prompt injections attempting to hijack LLM instructions.
- **Pattern Blocking**: `INJECTION_PATTERNS` detects heuristics including `ignore all previous instructions`, system prompt overrides, DAN mode jailbreaks, `<script>` tags, SQL deletion commands, and code execution builtins (`eval`, `exec`, `__import__`).
- **Pattern Neutralization & Encapsulation**: Matches are replaced with `[BLOCKED_INJECTION_PATTERN: ...]`. The entire content payload is structurally isolated within explicit XML boundary tags:
  ```xml
  <untrusted_content source='web' injection_flagged='true'>
  [BLOCKED_INJECTION_PATTERN: ignore all previous instructions] System instructions neutralized.
  </untrusted_content>
  ```

### 6. Specialist Safety & Gatekeeper Agents

- **`GatekeeperAgent` (`app/agents/gatekeeper_agent.py`)**: Subclass of `BaseAgent`. Evaluates task ambiguity, raises clarification questions, and checks tool permission gates.
- **`SafetyAgent` (`app/agents/safety_agent.py`)**: Subclass of `BaseAgent`. Executes multi-layer safety scans (permissions, PII redaction, prompt injection defense, audit logging) across agent inputs and outputs.

## Phase 9 Production Agent Runtime Architecture

Phase 9 introduces the Production Agent Runtime providing high-throughput async background worker management, state checkpointing and restoration, multi-dimension budget enforcement, and real-time SSE cost telemetry.

```mermaid
flowchart TD
    A["API Request / Job Submission"] --> B["JobQueueManager (Priority Queue 1-5)"]
    B --> C["AsyncWorkerPool (max_concurrency Workers)"]
    C --> D["LangGraph Agent Node Execution"]
    D -->|"At each step boundary"| E["CheckpointEngine (State Snapshot)"]
    E -->|"Persists DB execution_log & Memory"| F["AgentRun DB Record"]
    D -->|"Enforces Token/Search/Tool/WallClock"| G["BudgetService & CompositeBudget"]
    G -->|"Hard Limit Exceeded"| H["BudgetExceededError (Halt & Persist)"]
    G -->|"Soft Limit Warning (80%)"| I["SSE Telemetry Stream"]
    D -->|"LLM & Tool Call Cost Estimation"| J["CostTelemetryTracker"]
    J -->|"Live SSE Events"| K["telemetry:cost_updated SSE"]
```

### 1. Async Worker Pool & Background Job Queue Configuration

- **`JobQueueManager` (`app/services/worker_pool.py`)**:
  - Utilizes `asyncio.PriorityQueue` wrapped with `PriorityJobWrapper` sorting jobs by priority integer ($1$ is highest priority, $5$ is default) and creation timestamp.
  - Job status state machine: `queued` $\rightarrow$ `running` $\rightarrow$ `completed` / `failed` / `paused` / `cancelled` / `recovering`.
  - Automatic retry handler: retries failed tasks up to `max_retries` (default $3$) before transitioning to `failed` status.
- **`AsyncWorkerPool` (`app/services/worker_pool.py`)**:
  - Manages background worker task loops (`_worker_loop`) up to `max_concurrency` (default $4$).
  - Workers pull jobs asynchronously from `JobQueueManager`, track task heartbeats (`heartbeat_at`), handle cancellation signals (`asyncio.CancelledError`), and dispatch execution handlers registered via `register_handler(task_type, handler)`.
  - Global singleton instance: `global_worker_pool`.

### 2. Step Checkpointing Engine & State Resumption APIs

- **`CheckpointEngine` (`app/services/checkpoint_engine.py`)**:
  - Captures step-level snapshots of `AgentState`, extracted claims, scored sources, and agent outputs (`decision_matrix`, `data_analysis_results`, `visualization_spec`, `critique_report`, `hypotheses`).
  - Serializes datetime, UUID, set, and Pydantic types via `custom_json_serializer`.
  - Stores checkpoints in memory (`_checkpoints[run_id]`) and synchronizes with SQLAlchemy DB (`AgentRun.execution_log["checkpoints"]`).
- **State Resumption Workflow (`resume_run_from_checkpoint`)**:
  - Deserializes state snapshot from `checkpoint_id`, `step_name`, or latest checkpoint.
  - Reconstructs full typed `AgentState` dictionary ensuring seamless graph execution resumption without re-running earlier steps.

### 3. Multi-Dimension Budget Service Integration

- **`BudgetService` & `CompositeBudget` (`app/services/budget_service.py`)**:
  - Tracks usage across 4 distinct dimensions:
    1. `TokenBudget`: Prompt tokens, completion tokens, total tokens vs `max_tokens` (default $100,000$).
    2. `SearchBudget`: Web and database queries vs `max_searches` (default $20$).
    3. `ToolBudget`: Aggregate tool executions vs `max_tool_calls` (default $50$).
    4. `WallClockBudget`: Execution duration vs `max_seconds` (default $300.0$s / 5 minutes).
  - Enforces hard limits by raising `BudgetExceededError` and soft limits by emitting warning messages at $80\%$ utilization threshold.
  - Bounded sub-task budgets (`create_sub_task_budget`) ensuring sub-workstreams cannot exceed parent run remaining capacity.
  - Global singleton instance: `budget_service`.

### 4. Real-Time SSE Cost Telemetry Service

- **`CostTelemetryTracker` (`app/services/cost_telemetry.py`)**:
  - Calculates estimated USD costs per LLM call (`estimate_llm_cost`) based on model pricing (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro/Flash) per 1,000 tokens.
  - Calculates tool call costs (`estimate_tool_cost`) per execution (`web_search`, `python_sandbox`, `fact_checker`).
  - Streams real-time SSE cost events over `stream_service`:
    - `telemetry:cost_updated`: Incremental cost and running total metrics.
    - `telemetry:budget_updated`: General budget usage update.
    - `telemetry:budget_warning`: Soft budget limit warning.
    - `telemetry:budget_exceeded`: Hard budget limit error.
  - Global singleton instance: `cost_telemetry_tracker`.

## Phase 12 Continuous Intelligence & Project Memory Architecture

Phase 12 equips RADIS with autonomous continuous research monitoring, baseline delta comparison, quantitative materiality scoring, persistent project memory, domain research heuristics, and context injection into multi-agent prompt loops.

### 1. Architecture Overview

```mermaid
flowchart TD
    A["Research / Decision Execution State"] --> B["BaselineDeltaService"]
    B --> C["ResearchBaselineSnapshot"]
    
    D["MonitoringSchedulerService"] -->|Poll / Schedule| E["MonitoringJob (CRON / INTERVAL)"]
    E --> F["MonitoringAgent"]
    
    F -->|Fetch Baseline & Current State| B
    B -->|Compute State Diffs| G["MaterialityScoringEngine"]
    G -->|M = 0.35*S_assump + 0.25*S_contra + 0.25*S_matrix + 0.15*S_src| H["MaterialityScoreBreakdown"]
    
    H -->|M >= alert_threshold| I["DecisionAlertingService"]
    I --> J["DecisionAlert (UNREAD)"]
    I -->|Dispatch| K["Webhook URL"]
    
    A -->|Finished Run State| L["MemoryAgent"]
    L -->|Harvest Facts & Assumptions| M["ProjectMemoryService"]
    M --> N["ProjectMemoryItem (human_approval_status=PENDING)"]
    L -->|Save Untrusted Domains & Patterns| O["HeuristicsStoreService"]
    O --> P["ResearchHeuristics"]
    
    Q["Human Operator"] -->|Approve Assumption| M
    M -->|human_approval_status=APPROVED| N
    
    N --> R["MemoryContextInjector"]
    P --> R
    R -->|format_context_for_prompt| S["Agent Prompt Context Block"]
```

Key Phase 12 modules in [`backend/app`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app):
- **Continuous Monitoring Models & Services (`app/models/monitoring.py`, `app/services/monitoring_scheduler_service.py`)**: Manage scheduled jobs, 5-field cron parsing, interval runs, and log persistence.
- **Baseline Delta Engine (`app/services/baseline_delta_service.py`)**: Snapshot creation (`create_baseline_snapshot`, `create_snapshot_from_query`) and state diffing.
- **Materiality Scoring Engine (`app/services/materiality_scoring_engine.py`)**: Quantitative composite materiality formula.
- **Decision Alerting Service (`app/services/decision_alerting_service.py`)**: Alert lifecycle management (`UNREAD`, `ACKNOWLEDGED`, `RESOLVED`) and webhook notification dispatch.
- **Project Memory Engine (`app/models/project_memory.py`, `app/services/project_memory_service.py`)**: Cross-session persistent storage for facts, decision trails, reusable assumptions, prior conclusions, and lessons learned.
- **Domain Heuristics Store (`app/services/heuristics_store_service.py`)**: Learning heuristics tracking untrusted domain blacklists, effective query templates, verified tool execution patterns, and failure modes.
- **Memory Context Injector (`app/services/memory_context_injector.py`)**: Aggregates active, approved project memory items and domain heuristics, building a structured context block injected into agent prompts.
- **Specialized Phase 12 Subagents (`app/agents/monitoring_agent.py`, `app/agents/memory_agent.py`)**: Specialist subagents inheriting from `BaseAgent` implementing typed input/output AGENTS.md contracts (`agent_contracts.py`).

---

### 2. Continuous Monitoring Job Scheduling (`MonitoringSchedulerService`)

The [`MonitoringSchedulerService`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/services/monitoring_scheduler_service.py) handles continuous job scheduling, cron parsing, interval calculation, manual triggers, and execution log management:

1. **Schedule Types**:
   - **`CRON`**: Parsed via `calculate_next_cron_time` for standard 5-field cron syntax (`minute hour day-of-month month day-of-week`). Supports wildcards (`*`), steps (`*/N`), ranges (`A-B`), lists (`A,B`), and standard cron shorthands (`@daily`, `@hourly`).
   - **`INTERVAL`**: Frequency specified in seconds (`interval_seconds >= 10`). `calculate_next_run_at` computes `next_run_at = now + timedelta(seconds=interval_seconds)`.
   - **`EVENT_DRIVEN`**: Triggered externally on specific event notifications.
2. **Job Lifecycle**:
   - `create_job(job_in)`: Validates schedule syntax and persists `MonitoringJob` with initial `next_run_at`.
   - `trigger_job_now(job_id, current_state)`: Executes an immediate manual run via `execute_job`, updating `last_run_at`, incrementing `run_count`, logging execution in `MonitoringExecutionLog`, and calculating `next_run_at`.
   - `update_job(job_id, job_in)`: Supports pausing (`status = PAUSED`), resuming (`status = ACTIVE`), or updating schedule/threshold configurations.

---

### 3. Baseline Delta Engine (`BaselineDeltaService`)

The [`BaselineDeltaService`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/services/baseline_delta_service.py) constructs state snapshots and computes state deltas between baselines and new research runs:

1. **Snapshot Creation**:
   - `create_baseline_snapshot(snapshot_in)`: Persists structured snapshots (`claims_snapshot`, `sources_snapshot`, `assumptions_snapshot`, `decision_snapshot`).
   - `create_snapshot_from_query(query_id, snapshot_label)`: Automatically compiles a baseline snapshot by querying existing `Query`, `Claim`, `Source`, and `Decision` records associated with `query_id`.
2. **Delta Calculation (`compute_delta`)**:
   - **$S_{\text{assumption}}$**: Ratio of baseline assumptions present in `invalidated_assumptions` or marked as `INVALIDATED` / `REJECTED` in current state.
   - **$S_{\text{contradiction}}$**: Weighted ratio of claim contradictions ($0.4 \times C_{\text{contra}}$) and new claims ($0.1 \times C_{\text{new}}$) relative to total baseline claims.
   - **$S_{\text{matrix}}$**: Evaluates decision matrix drift. Automatically yields $S_{\text{matrix}} = 1.0$ if the primary recommendation flips (`recommendation_flipped = True`), or measures confidence score drift ($2.0 \times |\Delta \text{confidence}|$).
   - **$S_{\text{source}}$**: Ratio of low-quality sources ($\text{quality\_score} < 0.4$) or untrusted domain matches ($0.3 \times N_{\text{untrusted}}$).

---

### 4. Mathematical Materiality Formula (`MaterialityScoringEngine`)

The [`MaterialityScoringEngine`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/services/materiality_scoring_engine.py) calculates the composite materiality score $M \in [0.0, 1.0]$ using a weighted multi-factor linear equation:

$$M = 0.35 \times S_{\text{assumption}} + 0.25 \times S_{\text{contradiction}} + 0.25 \times S_{\text{matrix}} + 0.15 \times S_{\text{source}}$$

Where sub-scores are bounded in $[0.0, 1.0]$:
- $S_{\text{assumption}} \in [0.0, 1.0]$: Assumption invalidation sub-score (Weight: $0.35$).
- $S_{\text{contradiction}} \in [0.0, 1.0]$: Claim contradiction & addition sub-score (Weight: $0.25$).
- $S_{\text{matrix}} \in [0.0, 1.0]$: Decision option score drift & recommendation flip sub-score (Weight: $0.25$).
- $S_{\text{source}} \in [0.0, 1.0]$: Source reliability & untrusted domain match sub-score (Weight: $0.15$).

#### Materiality Level Classification Table

| Materiality Level | Score Range | Description & Action |
| :--- | :--- | :--- |
| `NEGLIGIBLE` | $M < 0.20$ | Minor delta; routine execution logging without notification |
| `LOW` | $0.20 \le M < 0.40$ | Minor claim or source updates; logged for informational review |
| `MEDIUM` | $0.40 \le M < 0.60$ | Moderate delta; notification logged; alert triggered if threshold $\le M$ |
| `HIGH` | $0.60 \le M < 0.80$ | Significant assumption invalidation or decision matrix drift; high priority alert |
| `CRITICAL` | $M \ge 0.80$ | Recommendation flip or severe assumption rejection; critical priority decision alert dispatched to webhook |

---

### 5. Project Memory Context Injection (`MemoryContextInjector`)

The [`MemoryContextInjector`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/services/memory_context_injector.py) injects active, approved project memory items and domain heuristics into agent prompt context blocks:

1. **Strict Human-in-the-Loop Approval Rule**:
   - Candidate assumptions harvested from research runs are stored with `human_approval_status = PENDING`.
   - `MemoryContextInjector` **strictly filters** memory items, only injecting items with:
     $$\text{human\_approval\_status} \in \{\text{'APPROVED'}, \text{'NOT\_REQUIRED'}\}$$
   - Pending or rejected assumptions are excluded from context injection until explicitly approved via `POST /api/v1/memory/items/{id}/approve`.
2. **Context Formatting (`format_context_for_prompt`)**:
   Outputs a structured Markdown context block:
   ```markdown
   ### PERSISTENT PROJECT MEMORY CONTEXT ###

   #### Active Project Facts:
   - [fact_key_1] Fact summary description... (Confidence: 0.95)

   #### Validated Reusable Assumptions:
   - [assumption_key_1] Approved assumption summary... (Status: APPROVED)

   #### Domain Research Heuristics (finance):
   - Untrusted Source Domains: unreliable-blog.com, speculative-news.net
   - Effective Query Templates: {company} SEC Form 10-K filing financial metrics
   ```

---

### 6. Specialist Subagents (`MonitoringAgent` & `MemoryAgent`)

Both subagents inherit from `BaseAgent`, enforce AGENTS.md Rule 9 tool auditing, and utilize typed contracts:

1. **`MonitoringAgent` ([`app/agents/monitoring_agent.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/monitoring_agent.py))**:
   - **Allowed Tools**: `["search_web", "query_database", "compute_delta"]`
   - **Input Contract**: `MonitoringAgentInput(job_id, current_state, alert_threshold)`
   - **Output Contract**: `MonitoringAgentOutput(job_id, execution_log_id, status, materiality_score, materiality_level, delta_summary, alert_triggered, alert_id, stop_reason, summary_message)`
   - Performs DB-backed or standalone delta calculations, calculates $M$, logs executions, and generates alerts when $M \ge \text{alert\_threshold}$.

2. **`MemoryAgent` ([`app/agents/memory_agent.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/memory_agent.py))**:
   - **Allowed Tools**: `["search_memory", "store_memory", "update_memory", "get_heuristics"]`
   - **Input Contract**: `MemoryAgentInput(action, project_id, session_id, memory_type, memory_item, domain, query, run_state)`
   - **Output Contract**: `MemoryAgentOutput(is_success, action_performed, items, context, heuristic, stop_reason, message)`
   - Actions: `HARVEST` (extracts durable facts with `human_approval_status = APPROVED` and candidate assumptions with `human_approval_status = PENDING`), `STORE`, `RETRIEVE`, `UPDATE`, `INVALIDATE`, `HEURISTIC_LOOKUP`.

## Testing & Audit Commands

**Backend:**
- Module imports check: `python -c "import app.models; import app.schemas; import app.agents; import app.tools; import app.services; import app.api.v1.router"`
- Pytest Unit & Contract Tests: `python -m pytest tests/`
- Ruff Linter: `ruff check app`
- Type checking: `mypy app`

**Frontend:**
- Vite Production Build: `npm run build`
- React Doctor Quality Audit: `npx react-doctor .` (Audited: **100/100 Great score**)


