# Developer Guide

Welcome to the Research And Decision Intelligence System (RADIS) developer documentation. This guide provides an overview of the architecture, setup instructions, and engineering rules.

## Architecture Overview

RADIS is structured as a monorepo containing a Python backend and a pure JavaScript Vite + React frontend styled 1-to-1 with the Stitch MCP Design System.

- **Backend (`/backend`)**: Built with FastAPI and Python 3.12. It handles database interactions via async SQLAlchemy (supporting SQLite for local dev & PostgreSQL for production), orchestrates multi-agent workflows using a custom `BaseAgent` framework, manages LLM interactions, and exposes REST endpoints and Server-Sent Events (SSE) streams.
- **Frontend (`/frontend`)**: A pure JavaScript React application powered by Vite (running natively on **port 5173**). Rebuilt to align 1-to-1 with the Stitch MCP UI Prototype (`RADIS Decision Command Center`). Styled with Tailwind CSS, Google Material Symbols, micro-caps typography, radar hero animations, live telemetry stream timelines, and zero non-functional buttons or dummy fallbacks. Audited with `react-doctor` (**100/100 Great score**).

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

## Testing & Audit Commands

**Backend:**
- Module imports check: `python -c "import app.models; import app.schemas; import app.agents; import app.tools; import app.services; import app.api.v1.router"`
- Ruff Linter: `ruff check app`
- Type checking: `mypy app`

**Frontend:**
- Vite Production Build: `npm run build`
- React Doctor Quality Audit: `npx react-doctor .` (Audited: **100/100 Great score**)
