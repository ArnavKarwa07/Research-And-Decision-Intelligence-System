# Changelog

All notable changes to the Research And Decision Intelligence System (RADIS) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] / [15.0.0] - RADIS Decision Engine Overhaul - 2026-09-05

### Added (RADIS Decision Engine Overhaul)
- **Rotational LLM Provider & Dynamic Error Failover (`RotationalGeminiProvider`, `RotationalChatGoogleGenerativeAI`)**:
  - Implemented automatic model rotation across candidate list `["gemini-flash-latest", "gemini-flash-lite-latest", "gemini-1.5-flash", "gemma-2-27b-it", "gemma-2-9b-it"]` in [`llm_provider.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/llm_provider.py) and [`graph.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/graph.py).
  - Handles API rate limits (HTTP 429), service unavailability (503), model missing errors (404), and quota exhaustion by dynamically failing over to the next candidate model without crashing research workflows.
- **Multi-Source Web Search Aggregator & Source Balancing (`WebSearchTool`)**:
  - Combined `ddgs` Python library, DuckDuckGo Lite/HTML scrapers, Wikipedia REST API, and arXiv API into a concurrent multi-source web intelligence aggregator in [`web_search.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/tools/web_search.py).
  - Enforced source balancing rules: caps academic literature from arXiv at $\le 2$ items and applies round-robin interleaving across live web, news, Wikipedia, and arXiv items.
  - Features query-parameterized news/market fallback sources (Google Scholar, Economic Times, Yahoo Finance, BBC News) when primary scrapers return zero results.
- **Content-First Synthesis & Dynamic Snippet-Grounded Offline Fallbacks (`SynthesisAgent`)**:
  - Upgraded [`synthesis.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/synthesis.py) with content-first sentence extraction from verified claims and web snippets.
  - Dynamically builds articulate, topic-grounded strategic recommendation options without mechanical title concatenation or static canned templates.
- **Prompt Injection XML Shielding (`synthesis_node`, `graph.py`)**:
  - Enforces `<retrieved_snippets>` XML boundary encapsulation around external web search snippets and RAG context blocks across all state machine graph nodes.
- **Robust Decision Agent Matrix Processing (`DecisionAgent`)**:
  - Enhanced [`decision.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/decision.py) to automatically enrich missing criteria scores with neutral baseline values ($0.5$), preventing matrix calculation exceptions.

## [1.1.0] - Multi-Source Web Search Aggregator & Gemini LLM Alignment - 2026-09-05

### Added (Multi-Source Web Search Aggregator & Gemini Alignment)
- **Multi-Source Web Search Aggregator ([`web_search.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/tools/web_search.py))**:
  - Concurrent multi-source search pipeline gathering live web results across **DuckDuckGo Lite / HTML**, **Wikipedia REST API**, **arXiv API**, and curated **News/Market Fallbacks** (Google Scholar, Economic Times, Yahoo Finance, Reuters, MarketWatch, Bloomberg).
  - Source distribution skew prevention: Guarantees balanced search result distribution across general live web news, encyclopedia context, academic literature, and financial telemetry without dropping general web/news sources when Wikipedia or arXiv return results.
  - Automatic SSL fallback context creation and robust HTTP exception handling.
- **Gemini LLM Provider Alignment (`gemini-flash-latest`)**:
  - Direct alignment of Google Gemini provider configurations in [`app/config.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/config.py), [`llm_provider.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/llm_provider.py), and [`graph.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/graph.py) to `gemini-flash-latest`.
  - Unified configuration parameter handling across `gemini_model`, `gemini_api_key`, `google_search_api_key`, and `google_search_engine_id`.
- **Dynamic Report Synthesis & Decision Engine (`SynthesisAgent`, `synthesis_node`)**:
  - Complete elimination of legacy static fallback template options, corporate jargon defaults, and hardcoded domain options (e.g., React/Next.js domain hardcoding).
  - Dynamic generation of topic-grounded strategic recommendations, weighted alternative trade-off matrices, best/base/worst scenarios, and decision tripwires directly from live evidence streams.

### Fixed (Bug Fixes BUG-01 through BUG-07)
- **BUG-01 (CRITICAL - Source Distribution Skew & DDG Scraper Failure)**: Fixed DuckDuckGo Lite 202/403 automated request failures causing 100% arXiv/Wikipedia skew by decoupling fallback web/news injection and executing concurrent multi-source aggregation.
- **BUG-02 (MINOR - Configuration Key Mismatch)**: Resolved configuration key name mismatch between [`config.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/config.py) (`google_search_api_key`, `google_search_engine_id`) and [`web_search.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/tools/web_search.py) (`GEMINI_API_KEY`, `GOOGLE_CX`) by unifying key lookup across environment variables and settings.
- **BUG-03 (MAJOR - Structured LLM Generation Type Error)**: Fixed `MockProvider.generate_structured()` crashing when validating Pydantic models containing generic list annotations (`list[T]` / `List[T]`).
- **BUG-04 (CRITICAL - Synthesis Node Array Index Out of Bounds)**: Resolved [`graph.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/graph.py) `synthesis_node` crashing with `IndexError`/`KeyError` when LLM responses contained a single alternative option or non-standard key names by adding safety bounds checks.
- **BUG-05 (MAJOR - Leftover Hardcoded Domain Templates)**: Removed leftover hardcoded React/Next.js domain templates from [`synthesis.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/synthesis.py) in favor of fully dynamic LLM-driven synthesis.
- **BUG-06 (MAJOR - Graph Architecture Stubbed Nodes)**: Replaced stubbed mock nodes in [`graph.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/graph.py) (`retrieval_node`, `fact_check_node`, `contradiction_node`) with real live Qdrant vector store RAG, real claim verification, and contradiction detection.
- **BUG-07 (MAJOR - Prompt Injection in Synthesis Node)**: Fixed prompt injection vulnerability in [`graph.py`](file:///c:/Users/user/OneDrive/Desktop/CODE/Research-And-Decision-Intelligence-System/backend/app/agents/graph.py) `synthesis_node` by encapsulating untrusted external web search snippets in `<retrieved_snippets>` XML boundaries and applying strict injection sanitization.

## [14.0.0] - Dynamic Orchestrator & Dynamic LLM Report Synthesis - 2026-09-05

### Added (Dynamic Orchestrator & Dynamic LLM Report Synthesis)
- **Dynamic Orchestrator-Subagent Graph Routing (`route_after_synthesis`, `route_after_decision`)**:
  - `route_after_synthesis`: Dynamically evaluates research execution mode (`quick`, `deep`, `comprehensive`, `adversarial`). In `quick` mode, execution skips deep hypothesis decomposition, falsification, and red-team critic loops, routing straight from `synthesis` to `decision` for fast response times.
  - `route_after_decision`: Dynamically inspects user intent and query context. Simple informational queries terminate cleanly at `__end__`, while quantitative queries (`sql`, `database`, `table`, `metrics`, `chart`, `sales`, `revenue`) conditionally trigger `data` and `visualization` nodes. Projects/sessions route to `memory`, and active monitoring jobs route to `monitoring`.
  - Intent-Based Fast-Path Query Router (`query_service.py`): Automatically classifies user query intent and bypasses unnecessary subagent nodes when deep multi-agent RAG or falsification is not required.
- **Complete Elimination of Canned Corporate Jargon Templates**:
  - **Zero-Boilerplate Dynamic LLM Report Synthesis (`SynthesisAgent`, `synthesis_node`)**: Pruned legacy hardcoded fallback templates containing ungrounded corporate jargon (such as "Regional Buffer Architecture", "Lithography", "Fabrication lead times", or generic "Monolithic Execution vs Multi-Agent Parallel Runtime" defaults).
  - **Context-Aware Dynamic LLM Prompting (`get_langchain_llm`)**: Modernized LLM synthesis integration using live Google Gemini / OpenAI providers with strict prompt guardrails ("DO NOT use generic corporate jargon... Tailor ALL recommendations directly to query topic"). Dynamically formats up to 6 verified evidence claims and raw RAG snippets into context blocks.
  - **5-Section Executive Deep Research Report Format**:
    1. Executive Summary & Core Strategic Recommendation (clear choice, confidence score, rationale)
    2. In-Depth Operational & Technical Analysis (addressing query topic key dynamics, pros, cons)
    3. Verified Evidence Trail & Fact-Checked Claims
    4. Key Risks, Assumptions & Tipping Point Triggers
    5. Actionable Implementation Roadmap (Phase 1 Immediate, Phase 2 Medium Term, Phase 3 Scale)
  - **Topic-Grounded Strategic Alternatives**: Generates topic-tailored alternative options and weighted trade-off scores dynamically aligned with the user query (e.g. React vs Full-Stack options when the query focuses on React frontend development).
- **Automated Anti-Jargon & Dynamic Routing Test Suite (`backend/tests/test_dynamic_synthesis_no_jargon.py`)**:
  - Automated pytest test suite validating:
    - Complete absence of canned corporate jargon across generated reports.
    - Topic relevance of generated strategic alternatives.
    - Dynamic graph routing correctness across execution modes and query intents.
- **Frontend Response & Intent UI Enhancements (`ChatConversationView.jsx`, `QueryInput.jsx`, `App.jsx`, `DecisionAnalyticsView.jsx`, `KnowledgeMemoryView.jsx`)**:
  - Unified response card view rendering dynamic executive research markdown reports with live stream telemetry.
  - Plus menu integration, fast-path intent indicator badges, and streamlined input area with simplified action controls.

## [13.0.0] - Phase 13 Release - 2026-09-05

### Added (Phase 13 Enterprise Expansion)
- **Enterprise Connectors Engine (`EnterpriseConnector`, `ConnectorSyncJob`, `ConnectorItemLog`, `BaseConnector`)**: Extensible connector framework supporting 5 enterprise data stores (**Google Drive**, **Notion**, **Slack**, **Gmail**, **SharePoint**). Features automated credential authorization (base64/AES-256 encrypted storage), differential polling/webhook sync, content-aware text chunking, and multi-tenant vector embedding into Qdrant knowledge bases (`enterprise_connectors_{workspace_id}`).
- **Sync Health & Rate Limit Monitoring (`ConnectorSyncService`)**: Real-time connector job dispatching, health state tracking (`IDLE`, `SYNCING`, `PAUSED`, `ERROR`, `COMPLETED`), last sync timestamp, API rate limit status, items processed/failed metrics, and automatic retry handling.
- **Fine-Grained Role-Based Access Control (`RBACService`, `Organization`, `Workspace`, `WorkspaceMember`, `ProjectShare`)**: 4-tier granular permission model (`OWNER`, `ADMIN`, `RESEARCHER`, `VIEWER`) regulating access across workspaces, tasks, memory stores, connectors, and audit logs with FastAPI dependency enforcement (`RBACService.has_permission`).
- **Single Sign-On & Token Session Revocation (`SSOAuthService`, `AuthTokenSession`)**: Enterprise SSO authentication supporting Google, Azure AD, Okta, SAML 2.0, and a built-in Mock Enterprise IdP endpoint (`/api/v1/auth/sso/mock-idp`). Issues SHA-256 hashed JWT sessions with instant token revocation blacklist capabilities (`revoke_session`).
- **Immutable Organizational Audit Logging (`EnterpriseAuditService`, `EnterpriseAuditLog`)**: Immutable compliance logging engine recording data access events, connector sync jobs, RBAC role changes, SSO logins, and admin governance overrides. Includes automatic PII scanning and redaction (`scan_and_redact_pii`).
- **Specialized Phase 13 Subagents (`ConnectorAgent`, `GovernanceAgent`)**:
  - `ConnectorAgent`: Specialized subagent handling data connector sync execution, chunking, and vector collection indexing.
  - `GovernanceAgent`: Specialized subagent executing RBAC permission audits, workspace boundary security, and immutable compliance audit reports.
- **Typed Agent Contracts & Pydantic Schemas (`agent_contracts.py`, `schemas/enterprise_connectors.py`, `schemas/rbac_auth.py`)**:
  - `ConnectorAgentInput` / `ConnectorAgentOutput`
  - `GovernanceAgentInput` / `GovernanceAgentOutput`
  - `ConnectorCreate` / `ConnectorUpdate` / `ConnectorResponse`
  - `SyncJobTriggerRequest` / `SyncJobResponse` / `ConnectorHealthStatus`
  - `OrganizationCreate` / `OrganizationResponse` / `WorkspaceCreate` / `WorkspaceResponse`
  - `WorkspaceMemberAdd` / `WorkspaceMemberUpdate` / `WorkspaceMemberResponse`
  - `SSOLoginRequest` / `SSOCallbackRequest` / `TokenResponse`
  - `AuditLogQueryFilter` / `EnterpriseAuditLogResponse`
- **Enterprise REST APIs**: 14 new endpoints under `/api/v1/connectors/*`, `/api/v1/auth/*`, `/api/v1/workspaces/*`, and `/api/v1/governance/*`.
- **Enterprise Research Workspace UI (`EnterpriseConnectorsWorkspace.jsx`, `GovernanceSecurityWorkspace.jsx`, `TeamWorkspaceSelector.jsx`, `HeaderAuthBar.jsx`)**: Full-featured React dashboards for connector configuration, sync health monitoring, RBAC member management, SSO authentication test flows, and audit log search.

## [12.0.0] - Phase 12 Release - 2026-09-05


### Added (Phase 12 Continuous Intelligence & Decision Monitoring)
- **Continuous Research Monitoring Engine (`MonitoringJob`, `ResearchBaselineSnapshot`, `MonitoringExecutionLog`, `DecisionAlert`)**: Automated continuous tracking of research topics, market conditions, and decision assumptions. Supports CRON (5-field cron parsing), INTERVAL (in seconds), and EVENT_DRIVEN schedules with alert thresholds and webhook URL notifications.
- **Persistent Project Memory Engine (`ProjectMemoryItem`, `ResearchHeuristics`)**: Multi-session persistent project memory storing active facts, decision trails, prior conclusions, reusable assumptions, and lessons learned. Includes domain-specific research heuristics (untrusted domain blacklists, effective query templates, verified tool execution patterns, and failure modes).
- **Mathematical Materiality Scoring Engine (`MaterialityScoringEngine`)**: Quantitative materiality calculation evaluating baseline state deltas across 4 weighted dimensions:
  $$M = 0.35 \times S_{\text{assumption}} + 0.25 \times S_{\text{contradiction}} + 0.25 \times S_{\text{matrix}} + 0.15 \times S_{\text{source}}$$
  Classifies delta impact into 5 materiality levels: `NEGLIGIBLE` ($M < 0.2$), `LOW` ($M < 0.4$), `MEDIUM` ($M < 0.6$), `HIGH` ($M < 0.8$), and `CRITICAL` ($M \ge 0.8$).
- **Baseline Delta Engine (`BaselineDeltaService`)**: Automated baseline snapshot creation (`create_baseline_snapshot`, `create_snapshot_from_query`) and state diffing tracking assumption invalidations ($S_{\text{assumption}}$), claim additions and contradictions ($S_{\text{contradiction}}$), decision matrix recommendation flips and score drifts ($S_{\text{matrix}}$), and source quality degradation or untrusted domain matches ($S_{\text{source}}$).
- **Project Memory Context Injector (`MemoryContextInjector`)**: Dynamically injects active facts, prior conclusions, validated reusable assumptions (enforcing Human-in-the-Loop `human_approval_status in ['APPROVED', 'NOT_REQUIRED']`), lessons learned, and domain heuristics into research and supervisor agent prompt context blocks (`format_context_for_prompt`).
- **Specialized Phase 12 Subagents (`MonitoringAgent`, `MemoryAgent`)**:
  - `MonitoringAgent`: Subagent executing monitoring job evaluations, calculating delta materiality, generating executive summaries, and triggering decision alerts.
  - `MemoryAgent`: Subagent inspecting completed research runs, harvesting durable facts, submitting candidate reusable assumptions for human approval (`human_approval_status = PENDING`), and updating domain heuristics.
- **Typed Agent Contracts & Pydantic Schemas (`agent_contracts.py`, `schemas/monitoring.py`, `schemas/project_memory.py`)**:
  - `MonitoringAgentInput` / `MonitoringAgentOutput`
  - `MemoryAgentInput` / `MemoryAgentOutput`
  - `BaselineSnapshotCreate` / `BaselineSnapshotResponse`
  - `MonitoringJobCreate` / `MonitoringJobUpdate` / `MonitoringJobResponse`
  - `MonitoringExecutionLogResponse` / `DecisionAlertResponse`
  - `ProjectMemoryItemCreate` / `ProjectMemoryItemUpdate` / `ProjectMemoryItemResponse`
  - `ResearchHeuristicCreate` / `ResearchHeuristicResponse`
  - `ProjectMemoryContext`
- **Continuous Intelligence REST APIs**: 19 new endpoints under `/api/v1/monitoring/*` and `/api/v1/memory/*`:
  - `POST /api/v1/monitoring/jobs`: Create continuous monitoring job.
  - `GET /api/v1/monitoring/jobs`: List monitoring jobs filtered by project, session, or status.
  - `GET /api/v1/monitoring/jobs/{id}`: Retrieve monitoring job details by ID.
  - `PATCH /api/v1/monitoring/jobs/{id}`: Update, pause, resume, or reconfigure monitoring job.
  - `DELETE /api/v1/monitoring/jobs/{id}`: Delete monitoring job.
  - `POST /api/v1/monitoring/jobs/{id}/run`: Trigger immediate manual run for a monitoring job.
  - `GET /api/v1/monitoring/jobs/{id}/logs`: Retrieve execution logs for a monitoring job.
  - `POST /api/v1/monitoring/baselines`: Create research baseline snapshot.
  - `GET /api/v1/monitoring/baselines/{id}`: Retrieve research baseline snapshot by ID.
  - `GET /api/v1/monitoring/alerts`: List decision alerts by job, project, session, severity, or status.
  - `POST /api/v1/monitoring/alerts/{id}/acknowledge`: Acknowledge decision alert.
  - `POST /api/v1/memory/items`: Create persistent project memory item.
  - `GET /api/v1/memory/items`: List memory items filtered by project, session, memory type, validity status, or approval status.
  - `GET /api/v1/memory/items/{id}`: Retrieve project memory item by ID.
  - `PATCH /api/v1/memory/items/{id}`: Update project memory item.
  - `POST /api/v1/memory/items/{id}/approve`: Approve or reject memory item or assumption (`APPROVED` / `REJECTED`).
  - `GET /api/v1/memory/heuristics`: Retrieve domain-specific research heuristics.
  - `POST /api/v1/memory/heuristics`: Add or update domain-specific research heuristics.
  - `POST /api/v1/memory/inject-context`: Preview project memory context injection for prompt generation.

## [11.0.0] - Phase 11 Release - 2026-09-04

### Added (Phase 11 Production UX & Artifact Export Package Engine)
- **Enterprise Research Workspace Shell (`App.jsx`)**: Upgraded top-level application navigation from basic inline chat stream into a full-featured 6-tab enterprise Research Workspace layout (`Plan`, `Evidence`, `Decision`, `Agent Activity`, `Sources Repository`, `Claims Graph`).
- **Interactive Plan & State Inspector (`PlanViewTab.jsx`)**: Dynamic visual graph of current research plan DAG, active subtasks, assigned subagent roles, dependencies, and state checkpoint inspector drawer.
- **Evidence Explorer & Claim Mapping (`EvidenceViewTab.jsx`)**: Dedicated Evidence View displaying verified findings, claim-to-source mapping, confidence meters, evidence status filters (`Supported`, `Contradicted`, `Inferred`, `Assumption`), and Evidence Editor integration.
- **Executive Decision Workspace & Weight Simulator (`DecisionViewTab.jsx`)**: Dedicated Decision View featuring primary recommendation banner, interactive MCDA comparison matrix (with dynamic criteria weight sliders), scenario simulations (Best/Base/Worst), sensitivity switch points, and decision tripwire triggers.
- **Agent Activity & Telemetry Workspace (`AgentActivityTab.jsx`)**: Dedicated real-time Agent Activity timeline view featuring Gantt execution visualization, live tool call stream, token/cost monitoring dashboard, and terminal telemetry logs modal.
- **Sources Repository & Domain Trust Index (`SourcesRepositoryTab.jsx`)**: Dedicated Sources repository view with search/filter tools, domain authority scores, publication dates, relevance scores, snippet previews, and source type filters (`Web`, `PDF`, `Database`, `Academic`).
- **Claims Taxonomy & Lineage Provenance Graph (`ClaimsGraphTab.jsx`)**: Dedicated Claims graph view with filterable claim-to-source mapping graph and matrix distinguishing `FACT`, `CALCULATION`, `INFERENCE`, `ASSUMPTION`, `PREDICTION`, `OPINION`, and `UNRESOLVED` claims with quality ratings.
- **Multi-Format Export Package Center & Generator (`ExportArtifactModal.jsx`, `ArtifactService`, `ExportPackageService`)**:
  - Automated generation of structured executive decision memos and technical research reports (Markdown & standalone styled HTML).
  - Tabular comparison exporter for MCDA criteria matrices as CSV and Markdown specs.
  - One-click multi-format downloadable `.zip` package archive containing `decision_memo.md`, `research_report.md`, `executive_summary.html`, `research_state.json`, `sources_manifest.csv`, and `mcda_comparison.csv`.
- **Artifact & Sources REST APIs (`artifacts.py`)**: Endpoints under `/api/v1/queries/{query_id}/artifacts/*` and `/api/v1/queries/{query_id}/sources` for memo compilation, report generation, comparison table exports, and ZIP package downloads.

## [10.0.0] - Phase 10 Release - 2026-09-04


### Added (Phase 10 LLMOps & Evaluation Framework)
- **Golden Benchmark Datasets (`GoldenDataset`, `GoldenTestCase`, `EvalRun`, `EvalResult`)**: Database ORM models and dataset service pre-seeded with 10+ standard decision and research test cases across 4 categories (`market_analysis`, `technical_feasibility`, `financial_evaluation`, `strategic_decision`).
- **Mathematical Evaluation Engine (`EvalMetricsEngine`)**: Comprehensive metric calculators for:
  - Vector/RAG Retrieval: `Precision@K`, `Recall@K`, `MRR`, `NDCG`.
  - Claim Verification: `Hallucination Rate`, `Faithfulness`, `Evidence Groundedness`.
  - Citation & Trajectory: `Citation Coverage`, `Citation Precision`, `Trajectory Efficiency`, `Tool Call Accuracy`, `Unnecessary Re-plan Penalty`.
  - Decision Quality: `MCDA Criteria Weighting Score`, `Scenario Payoff Alignment`, `Sensitivity Tipping Point Validity`.
- **OpenTelemetry & LangSmith Tracing (`OpenTelemetryService`)**: Hierarchical span context propagation across multi-agent execution graphs, tool calls, and LLM calls. Provides in-memory trace buffering and SSE telemetry streaming (`telemetry:span_started`, `telemetry:span_finished`).
- **Agent Timeline & Gantt Visualization (`AgentTimelineService`, `AgentTimelineGantt.jsx`)**: Real-time step-by-step Gantt execution timeline tracking and SSE event streaming (`telemetry:agent_timeline_step`).
- **Cost, Token & Latency Monitoring Dashboards (`CostTelemetryTracker`, `CostMetricsDashboard.jsx`)**: Granular metrics tracking token usage, latency distribution (p50, p90, p99 percentiles), and financial USD cost breakdown per agent role and model.
- **Automated Regression Evaluation Harness (`RegressionHarnessService`, `EvaluationDashboard.jsx`)**: Regression harness runner comparing evaluation runs against baseline quality/cost benchmarks, computing metric deltas, and enforcing quality drop (<5%) and cost increase (<15%) ceilings.
- **Specialist Evaluation Agent (`EvaluationAgent`)**: Dedicated agent implementing AGENTS.md typed contract (`EvaluationAgentInput`, `EvaluationAgentOutput`).
- **Evaluation & Observability REST APIs**: 10 new REST API endpoints under `/api/v1/eval` and `/api/v1/observability`:
  - `POST /api/v1/eval/datasets/seed`
  - `POST /api/v1/eval/datasets`
  - `GET /api/v1/eval/datasets`
  - `POST /api/v1/eval/datasets/{id}/cases`
  - `POST /api/v1/eval/runs`
  - `GET /api/v1/eval/runs/{id}`
  - `POST /api/v1/eval/regression/compare`
  - `GET /api/v1/observability/traces/{run_id}`
  - `GET /api/v1/observability/timeline/{run_id}`
  - `GET /api/v1/observability/metrics/dashboard`

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
