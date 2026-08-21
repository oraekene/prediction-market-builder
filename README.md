# Prediction Market Builder

A web-based prediction market terminal and strategy builder for Polymarket, Kalshi, and Drift — combining a hybrid chat + node-graph strategy interface with an AI research stack (Hermes-Agent orchestration, TabPFN inference, RLM archive mining, pi-autoresearch hypothesis engine).

See [docs/prd.md](docs/prd.md) for the product vision and [docs/implementation-plan.md](docs/implementation-plan.md) for the phased build plan.

## Layout

```
backend/          FastAPI + SQLAlchemy + Alembic API server
frontend/         React + TypeScript + Vite terminal UI
infrastructure/   docker-compose, Prometheus/Grafana, SearXNG, deploy scripts
docs/             PRD, plans, specs, ADRs, agent docs
```

## Quick start (local dev)

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Required secrets — generate real values:
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(48))")
export ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

The app refuses to start without `SECRET_KEY` (>= 32 chars) and `ENCRYPTION_KEY`.
Default database is SQLite (`pmbuilder.db`); set `DATABASE_URL` for Postgres.

### Frontend

```bash
cd frontend
npm ci
npm run dev     # http://localhost:5173, proxies /api and /ws to :8000
```

## Docker deployment

```bash
cp .env.example .env    # fill in every required value
docker compose -f infrastructure/docker-compose.yml up -d --build
docker compose -f infrastructure/docker-compose.yml exec backend alembic upgrade head
```

Services: frontend (:5173), backend (:8000), postgres+pgbouncer, redis,
searxng, prometheus (:9090), alertmanager, grafana (:3001), postgres-exporter.
Datastores bind internally; only the app and monitoring UIs are exposed.

## Tests

```bash
# Backend
cd backend && pytest tests/ -q

# Frontend
cd frontend && npx tsc --noEmit && npx vitest run
```

## Documentation

- `docs/prd.md` — product requirements, five-layer architecture, node catalog
- `docs/implementation-plan.md` — phased delivery plan
- `docs/unified-platform-roadmap.md`, `docs/user-guide.md`, `docs/api-reference.md`
- `docs/superpowers/` — design specs and implementation plans per feature
- `docs/adr/` — architecture decision records
- `CONTEXT.md` — domain glossary and current-state map
- `docs/teardown-2026-08-13.md` — security/architecture teardown this codebase was rebuilt from
