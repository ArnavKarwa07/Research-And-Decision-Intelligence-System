# Changelog

All notable changes to the Research And Decision Intelligence System (RADIS) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
