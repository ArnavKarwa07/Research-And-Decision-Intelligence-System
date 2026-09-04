# Changelog

All notable changes to the Research And Decision Intelligence System (RADIS) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [9.0.0] - Phase 9 Release - 2026-09-04

### Added (Phase 9 Production Agent Runtime)
- **Async Worker Pool & Priority Queue (`AsyncWorkerPool`, `JobQueueManager`)**: Background worker pool managing concurrent research job execution with configurable concurrency limits (`max_concurrency`), 5-level priority queue ordering (`PriorityJobWrapper`), worker loop lifecycle management (`start`, `stop`), automatic retries, heartbeat tracking, and job status state machine (`queued`, `running`, `completed`, `failed`, `paused`, `cancelled`, `recovering`).
- **Step-Level Checkpoint Engine (`CheckpointEngine`, `Checkpoint`)**: In-memory and persistent step-level state checkpointing engine capturing graph execution state snapshots (`AgentState`), extracted claims, scored sources, and agent outputs (`decision_matrix`, `data_analysis_results`, `visualization_spec`, `critique_report`, `hypotheses`). Includes `resume_run_from_checkpoint` for state deserialization and resumption.
- **Multi-Dimension Budget Enforcement (`BudgetService`, `CompositeBudget`)**: Real-time budget enforcement across 4 distinct dimensions: `TokenBudget` (prompt/completion tokens), `SearchBudget` (web and DB queries), `ToolBudget` (aggregate tool executions), and `WallClockBudget` (elapsed runtime seconds). Supports configurable soft limits (80% warning threshold) and hard limits (`BudgetExceededError`), along with sub-task budget allocation bounded by parent run capacity.
- **Real-Time SSE Cost Telemetry (`CostTelemetryTracker`, `estimate_llm_cost`, `estimate_tool_cost`)**: Real-time USD cost estimation engine for LLM model calls (GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro/Flash) and tool executions (`web_search`, `python_sandbox`, `fact_checker`). Emits real-time SSE cost telemetry events: `telemetry:cost_updated`, `telemetry:budget_updated`, `telemetry:budget_warning`, and `telemetry:budget_exceeded`.
- **Runtime Control REST APIs**: 4 new execution control endpoints available under both `/api/v1/runtime/runs` and `/api/runs` direct path aliases:
  - `POST /api/v1/runtime/runs/{id}/pause` (and `/api/runs/{id}/pause`): Pause an active research run.
  - `POST /api/v1/runtime/runs/{id}/resume` (and `/api/runs/{id}/resume`): Resume a paused or failed research run from the latest checkpoint.
  - `GET /api/v1/runtime/runs/{id}/checkpoints` (and `/api/runs/{id}/checkpoints`): Retrieve all step-level execution checkpoints for a run.
  - `GET /api/v1/runtime/runs/{id}/budget` (and `/api/runs/{id}/budget`): Retrieve multi-dimension budget tracking statistics and limit check status for a run.

## [8.0.0] - Phase 8 Release - 2026-09-04

### Added (Phase 8 Human-in-the-Loop & Safety Framework)
- **Approval Gates & 5-Minute Auto-Kill Timeouts (`ApprovalGate`, `HITLService`)**: Asynchronous approval gate management for high-risk tools (`python_sandbox`, `execute_sql_query`). Includes an automated 5-minute (300s) auto-kill timeout mechanism (`check_and_apply_timeouts`) that transitions pending gates to `EXPIRED` status to prevent pipeline deadlocks.
- **Clarification Questions (`ClarificationQuestion`)**: Interactive agent-to-user questioning workflow with optional multiple-choice response choices when research objectives are ambiguous or underspecified. Includes 5-minute timeout auto-kill.
- **User Evidence Overrides & Assumption Confirmations**: REST services (`override_claim_evidence`, `confirm_hypothesis_assumption`) allowing human operators to manually correct claim verification statuses or confirm/reject preliminary hypothesis assumptions.
- **Role-Based Tool Permission Scoping (`DEFAULT_ROLE_PERMISSIONS`, `SecurityService.check_tool_permission`)**: Fine-grained capability matrix mapping agent roles (`research`, `data_agent`, `supervisor`) to `allowed`, `denied`, and `requires_approval` tool access control lists.
- **PII Detection & Redaction Engine (`PII_PATTERNS`, `scan_and_redact_pii`)**: Automated regex and structure scanning detecting and redacting Email, Phone, SSN, API Tokens, Bearer Tokens, and Secret Passwords across strings, dicts, and arrays before persistence or UI rendering.
- **Indirect Prompt Injection & Jailbreak Defense (`INJECTION_PATTERNS`, `sanitize_untrusted_content`)**: Untrusted input scanner neutralizing prompt overrides, DAN mode jailbreaks, `<script>` tags, and dangerous code/SQL execution attempts with structural `<untrusted_content>` XML encapsulation.
- **Security Audit Logging (`AuditLog`, `SecurityService.log_audit_event`)**: Immutable audit log storage tracking critical security events (`approval_requested`, `approval_auto_killed_timeout`, `clarification_requested`, `prompt_injection_detected`, etc.) with sanitized PII details.
- **Specialist Safety Agents (`GatekeeperAgent`, `SafetyAgent`)**: Dedicated agents inheriting from `BaseAgent` for ambiguity detection, tool risk evaluation, PII redaction, and prompt injection defense.
- **Database Tables (`approval_gates`, `clarification_questions`, `audit_logs`)**: SQLAlchemy ORM models with index optimization, JSON payload fields, and ISO 8601 timestamps.
- **HITL & Safety REST APIs**: 10 new API endpoints under `/api/v1/hitl` and `/api/v1/safety`:
  - `GET /api/v1/hitl/approvals`
  - `POST /api/v1/hitl/approvals/{gate_id}/resolve`
  - `GET /api/v1/hitl/clarifications`
  - `POST /api/v1/hitl/clarifications/{question_id}/answer`
  - `POST /api/v1/hitl/evidence/override`
  - `POST /api/v1/hitl/assumptions/confirm`
  - `GET /api/v1/safety/audit-logs`
  - `GET /api/v1/safety/permissions`
  - `POST /api/v1/safety/scan-pii`
  - `POST /api/v1/safety/check-injection`

## [7.0.0] - Phase 7 Release - 2026-09-04

### Added (Phase 7 Data Agent & Data Visualization)
- **Data Investigation Agent (`DataInvestigationAgent`)**: Specialist subagent with typed contracts, AST safety guardrails, budget enforcement, and statistical breakdown.
- **Read-Only SQL Tool (`SQLTool`)**: Safe read-only SQL query execution on SQLite/PostgreSQL with AST keyword validation, table schema inspection, and limit injection.
- **CSV & Structured Data Tool (`CSVTool`)**: Native ingestion, parsing, data profiling, type inference, summary statistics, and automatic registration of uploaded CSV/XLSX files into SQLite tables.
- **Sandboxed Python Analysis Engine (`PythonSandboxTool`)**: Isolated Python sandbox with AST security validation, restricted builtins, AST module whitelisting (`safe_import`), execution timeout, and automated statistical metrics (mean, median, stddev, percentiles, correlation, trend analysis).
- **Chart Spec & Summary Table Tool (`ChartTool`)**: Programmatic generation of Vega-Lite JSON visualization specifications (bar, line, scatter, pie) and formatted summary tables with statistical findings.
- **Data Visualization Agent (`DataVisualizationAgent`)**: Specialist agent for converting raw data into interactive charts, summary tables, and embedded visual takeaways.
- **Data Models & Database Tables**: Added `UploadedDataset`, `DataQueryRecord`, `VisualizationSpec`, and `ReproducibleArtifact` models and tables.
- **Data Analysis REST APIs**: 6 new endpoints under `/api/v1/data`:
  - `POST /api/v1/data/datasets/upload`
  - `GET /api/v1/data/datasets/{dataset_id}/schema`
  - `POST /api/v1/data/query`
  - `POST /api/v1/data/analyze`
  - `POST /api/v1/data/visualize`
  - `GET /api/v1/data/artifacts/{query_id}`
- **Frontend Visualization Components**: `DataVisualizationCard.jsx` (interactive chart spec & summary table renderer) and `DataArtifactsModal.jsx` (reproducible execution artifacts inspector).
- **LangGraph Integration**: Integrated `data_node` and `visualization_node` into the LangGraph state machine.

## [6.0.0] - Phase 6 Release - 2026-09-04


### Added (Phase 6 Decision Intelligence)
- **Decision Framework (`DecisionAgent`)**: Structured multi-criteria decision analysis (MCDA) matrix, alternatives & criteria modeling, normalized weight calculation, risk tracking, and calibrated confidence scoring.
- **Scenario Simulation Engine (`run_scenario`)**: Best-case (25%), Base-case (50%), and Worst-case (25%) outcome projections across competing options with probability distributions.
- **Sensitivity Stress-Testing (`run_sensitivity`)**: Tipping point / crossover analysis detecting exact criteria weight thresholds where top-ranked recommendations flip.
- **Expected Value Engine (`calculate_expected_value`)**: Probabilistic payoff calculation ($EV = \sum P_k \times V_{ik}$) for decision options under uncertainty.
- **Decision Tripwires & Triggers (`DecisionTrigger`)**: Explicit event-driven conditions and thresholds that notify or necessitate recommendation re-evaluation.
- **Database Table (`decisions`)**: Dedicated `decisions` table with full SQLAlchemy model (`Decision`), cascade deletion, and query relationship.
- **Decision REST APIs**: 5 new endpoints for running, fetching, and re-running sensitivity/scenarios:
  - `POST /api/v1/queries/{query_id}/decisions`
  - `GET /api/v1/queries/{query_id}/decisions`
  - `GET /api/v1/decisions/{decision_id}`
  - `POST /api/v1/decisions/{decision_id}/sensitivity`
  - `POST /api/v1/decisions/{decision_id}/scenarios`
- **Frontend Decision Matrix UI Component (`DecisionMatrixCard.jsx`)**: Multi-tab UI displaying Executive Recommendation, Weighted Criteria Matrix, Best/Base/Worst Scenarios, Sensitivity Tipping Points, Expected Payoffs, and Decision Triggers.

## [5.0.0] - Phase 5 Release - 2026-09-04


### Added (Phase 5 Self-Challenge & Dynamic Re-planning)
- **Alternative Hypothesis Engine (`HypothesisAgent`)**: Automatic generation of 3-7 competing, falsifiable hypotheses for any research query, tracked with confidence scores and discriminating evidence criteria.
- **Falsification Agent (`FalsificationAgent`)**: Targeted inverse query formulation, counter-evidence collection, and net-weight confidence updates to systematically disconfirm preliminary hypotheses.
- **Critic / Red-Team Agent (`CriticAgent`)**: Independent red-team review auditing evidence quality (single-source, low confidence), logical coherence, completeness (omitted variables), and framing bias without shared state.
- **Dynamic Re-planning Loop**: Extended LangGraph conditional graph routing (`should_replan` / `replan_triggered`) allowing automatic loop-back to Research/Fact-Check nodes when red-team audit flags severe gaps (`HIGH` / `CRITICAL`).
- **Self-Challenge Service & REST Endpoints**: End-to-end self-challenge orchestration service exposing endpoints:
  - `POST /queries/{query_id}/hypotheses/generate`
  - `GET /queries/{query_id}/hypotheses`
  - `GET /hypotheses/{hypothesis_id}`
  - `POST /hypotheses/{hypothesis_id}/falsify`
  - `POST /queries/{query_id}/critique`
  - `POST /queries/{query_id}/self-challenge`
- **SSE Telemetry Events**: 6 new Server-Sent Event stream types: `hypothesis:generated`, `hypothesis:falsification_started`, `hypothesis:falsified`, `critique:report_generated`, `replan:triggered`, `self_challenge:completed`.
- **Database Schema Additions**: `hypotheses` and `critique_reports` tables with full SQLAlchemy models and CASCADE relationships to `queries`.
- **Agent Contracts**: Enforced Pydantic V2 schemas for `HypothesisAgentInput`/`Output`, `FalsificationInput`/`Output`, and `CriticInput`/`Output`.

## [4.0.0] - Phase 4 Release - 2026-09-04

### Added (Phase 4 Internal Knowledge + RAG)
- **Multi-Format Document Parser Engine**: Support for PDF, DOCX, TXT, and Markdown parsing via extensible `DocumentParserFactory` with metadata extraction (page numbers, section headings).
- **Hierarchical Semantic Chunking**: Parent-child hierarchical chunking strategy maintaining structural document context and precise text token windows.
- **Qdrant Dense Vector Store Integration**: Native Qdrant vector database client manager supporting per-session collection creation, dense payload storage, cosine distance index, and async vector deletion.
- **BM25 Sparse Search Engine**: In-memory BM25 ranker for lexical keyword matching over session document chunk corpora.
- **Hybrid Search & Reciprocal Rank Fusion (RRF)**: Combined dense vector and sparse lexical retrieval using RRF scoring with configurable weight alpha.
- **Cross-Encoder Reranking Engine**: Multi-stage reranking pipeline using cross-encoder scoring to elevate high-relevance chunks.
- **Citation Mapping & Attribution**: Real-time document chunk citation tracking (`[Doc: filename, Page: X, Chunk: Y]`) and context payload injection into agent LLM prompts.
- **Document Management & Search APIs**: RESTful ingestion, listing, chunking, SSE status streaming, and search endpoints (`/search/hybrid`, `/search/semantic`, `/search/keyword`).
- **Database Schema Additions**: `Document`, `DocumentChunk`, and `VectorCollection` tables for tracking document lifecycle, chunk hierarchies, and vector storage metadata.

## [3.0.0] - 2026-09-03

### Added (Phase 3 Evidence Intelligence)
- Atomic claim extraction & typing (7-type taxonomy)
- Source credibility, freshness, and independence scoring services
- Claim confidence engine with weighted formulas
- Fact Check Agent with 3 search strategies (Direct, Authority, Counter-evidence) and strict URL/content_hash deduplication
- Contradiction Agent with 5-check detection pipeline, severity scoring, and resolution state machine
- Provenance Agent & Evidence Graph engine
- Extended LangGraph workflow with conditional re-verification loops
- 9 new SSE event types (`claim:*`, `contradiction:*`, `source:*`, `evidence:graph_updated`)
- New API endpoints for claims, contradictions, evidence-graph, and user resolutions
- 6 new Frontend UI components (`ClaimsPanel`, `ContradictionsPanel`, `EvidenceGraphView`, `SourceScoringCard`, `UserResolutionModal`, SSE hook extensions)
- Database schema additions (`claims`, `claim_sources`, `source_groups`, `source_group_members`, `contradictions`, `sources` extensions)

## [2.0.0] - Phase 2 Release - 2026-09-03

### Added

**Multi-Agent Execution Core**
- Upgraded LangGraph state machine from a rigid 4-step workflow to a dynamic multi-agent execution runtime supporting 6 specialist agents: `SupervisorAgent`, `ResearchAgent`, `RetrievalAgent`, `EvidenceAgent`, `SynthesisAgent`, and `AdversarialAgent`.
- Implemented typed `AgentContracts` (`agent_contracts.py`) enforcing Pydantic V2 input/output schemas, stop conditions, and budget constraints across all agents per `AGENT_CONTRACTS.md`.
- Integrated durable `AgentRun` database persistence (`agent_run.py`) tracking sub-agent execution logs, step counts, token usage, and elapsed runtime.
- Built `RetrievalAgent` (`retrieval.py`) for semantic and keyword searches over internal project knowledge chunks.
- Built `EvidenceAgent` (`evidence.py`) for atomic claim extraction (`FACT`, `CALCULATION`, `INFERENCE`, `ASSUMPTION`), confidence scoring, and source provenance mapping.
- Built `SynthesisAgent` (`synthesis.py`) for executive report synthesis and alternative option trade-off matrix generation.
- Built `AdversarialAgent` (`adversarial.py`) for red-team falsification audits, unvalidated claim detection, and calibrated confidence adjustment.

**Frontend Command Center**
- Integrated `PlanGraphView.jsx` visualizing sub-task decomposition and specialist agent status badges.
- Integrated `DecisionMatrixCard.jsx` displaying primary recommendations, trade-off alternative scoring, calibrated confidence gauges, core assumptions, and key risks.

---

## [1.0.0] - Phase 1 Release - 2026-08-30

### Added

**Backend & Architecture**
- FastAPI core application implementation for high-performance async API endpoints (`/api/v1/sessions/`, `/api/v1/queries/`, `/api/v1/stream/`, `/api/v1/evidence/`).
- SQLAlchemy ORM models covering core entities: `Session`, `Query`, `Evidence`, and `Source` with async SQLite and PostgreSQL support.
- `BaseAgent` framework with strict enforcement for step constraints, token limits, and `asyncio.wait_for` timeout budgets.
- Centralized Tool Registry featuring JSON Schema validation, execution auditing, and SSRF security URL filtering (`is_safe_url`).
- Real live DuckDuckGo HTML web search integration (`_duckduckgo_search`) providing real live web results out-of-the-box with zero API key requirements.
- Server-Sent Events (SSE) stream service with async client disconnect detection.

**Frontend UI/UX (Stitch MCP 1-to-1 Rebuild)**
- Rebuilt frontend from scratch using pure JavaScript Vite React running natively on **port 5173**.
- Pixel-identical alignment with the **Stitch MCP UI Prototype** (`RADIS Decision Command Center`).
- Integrated Tailwind CSS, Google Material Symbols Outlined icons (`radar`, `search_insights`, `hub`, `science`, `send`, `check`, `sync`), micro-caps typography (`JetBrains Mono`), and concentric spinning radar hero animations.
- Completely pruned all non-functional links, dead buttons, and dummy data fallbacks.
- Integrated interactive **Terminal Logs Modal** (`TerminalLogsModal.jsx`) displaying raw SSE step telemetry.
- Audited with `react-doctor` achieving a **100 / 100 Great** quality score across 13 scanned files.
