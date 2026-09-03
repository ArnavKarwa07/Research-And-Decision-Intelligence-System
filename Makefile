.PHONY: dev dev-backend dev-frontend install install-backend install-frontend lint lint-backend lint-frontend typecheck test docker-up docker-down clean

# ── Full Stack ────────────────────────────────────────────────
dev: dev-backend dev-frontend

install: install-backend install-frontend

# ── Backend ───────────────────────────────────────────────────
install-backend:
	cd backend && pip install -e ".[dev]"

dev-backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

lint-backend:
	cd backend && python -m ruff check app/ tests/
	cd backend && python -m ruff format --check app/ tests/

typecheck-backend:
	cd backend && python -m mypy app/

test:
	cd backend && python -m pytest tests/ -v --cov=app --cov-report=term-missing

# ── Frontend ──────────────────────────────────────────────────
install-frontend:
	cd frontend && npm install

dev-frontend:
	cd frontend && npm run dev

lint-frontend:
	cd frontend && npx next lint

typecheck-frontend:
	cd frontend && npx tsc --noEmit

# ── Combined ──────────────────────────────────────────────────
lint: lint-backend lint-frontend

typecheck: typecheck-backend typecheck-frontend

# ── Docker ────────────────────────────────────────────────────
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

# ── Cleanup ───────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/dist backend/build backend/*.egg-info
	rm -rf frontend/.next frontend/out
