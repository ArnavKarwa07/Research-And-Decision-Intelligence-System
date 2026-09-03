# Changelog

All notable changes to the Research And Decision Intelligence System (RADIS) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
