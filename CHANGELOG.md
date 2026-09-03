# Changelog

All notable changes to the Research And Decision Intelligence System (RADIS) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
