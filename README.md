# AgriSat Risk

![CI](https://github.com/abdullah-dev5/agrisat-risk/actions/workflows/ci.yml/badge.svg)

Satellite-based parametric crop risk platform for agricultural lenders and insurers in Pakistan.

**MVP scope:** Wheat monitoring in Matiari District, Sindh — decision-support only (not automated payout).

## Architecture

```
frontend/     React 19 + TypeScript + Leaflet dashboard (pnpm)
backend/      Python FastAPI — tier adapters, fusion, risk scoring
supabase/     PostgreSQL + PostGIS, Auth, RLS, report storage
```

See [Architecture](docs/ARCHITECTURE.md) for the full system diagram, module map, and data flow.

### Three-tier data stack (FR-3.4)

| Tier | Source | Role |
|------|--------|------|
| 1 | PlanetScope (E&R Program) | 3m optical — deferred (M5), pending license |
| 2 | SEN2SR (local super-resolution model) + Sentinel-2 weekly composite fallback | 2.5m optical |
| 3 | Sentinel-1 SAR + Sentinel-2 + CHIRPS rainfall (via Google Earth Engine) | Always-available, cloud-independent baseline — **required, no synthetic fallback** |

Core risk flagging works on Tier 3 alone (FR-3.7); a live GEE service account is required for all field processing.

### Beyond the three tiers

- **Async processing** — registering or reprocessing a field returns immediately; satellite fetch/fusion/risk scoring runs in a background worker and the frontend polls `GET /fields/{id}/processing` until it's ready.
- **ML risk layer (M12)** — a gradient-boosted classifier can elevate (never downgrade) the z-score-based risk tier when its confidence is high enough; toggled via `ML_RISK_ENABLED`.
- **Tenant isolation (M1)** — every institution's data is scoped by `institution_id` at the application layer on every query; see [Architecture](docs/ARCHITECTURE.md#tenant-isolation) for how this relates to the Postgres RLS policies also defined in the schema.

## Quick start

### Prerequisites

- Node.js 20+
- pnpm 9+ (`npm install -g pnpm`)
- Python 3.11+
- [Supabase CLI](https://supabase.com/docs/guides/cli) (optional, for local DB)
- Google Earth Engine service account (Tier 3 pipeline)

### 1. Supabase

Create a project at [supabase.com](https://supabase.com), then run migrations:

```bash
supabase db push
# or paste supabase/migrations/001_initial_schema.sql in the SQL editor
```

Copy `.env.example` values into `backend/.env` and `frontend/.env`.

### 2. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open http://localhost:5173

## Environment variables

See `backend/.env.example` and `frontend/.env.example`.

## API docs

With the backend running: http://localhost:8000/docs

## Documentation

- [Architecture](docs/ARCHITECTURE.md) — system diagram, module map, data flow, tenant-isolation design
- [Module plan](docs/MODULE-PLAN.md) — delivery order and acceptance criteria (MVP complete)
- [Supabase setup](docs/SUPABASE-SETUP.md) — **start here after clone (M11)**
- [Google Earth Engine setup](docs/GEE-SETUP.md) — service account and GCP project configuration for Tier 3
- [Production deployment](docs/PRODUCTION.md) — Gunicorn, Docker, security, timeouts
- [Contributing](CONTRIBUTING.md) — dev workflow, branch/commit conventions, manual verification gate
- [Changelog](CHANGELOG.md) — notable changes by milestone
- [SRS traceability](docs/SRS-traceability.md) — requirement → code map
- [UI/UX inspiration](docs/UI-UX-INSPIRATION.md) — historical design-direction options from before the M9 Canopy redesign shipped
- [Audit findings](docs/AUDIT-FINDINGS.md) — prioritized backlog of known flaws and improvement ideas
- [Feature roadmap](docs/FEATURE-ROADMAP.md) — feasibility-checked future features, and which accelerators/evaluators to target
- [Free vs. paid resources](docs/FREE-VS-PAID-RESOURCES.md) — what's buildable at $0 today vs. what needs budget, and when
- [User flow & what the numbers mean](docs/USER-FLOW.md) — plain-language walkthrough of the product and honest accuracy caveats
- **In-app Guide** — http://localhost:5173/guide (plain-language + technical tutorials)

## Automated tests

```bash
cd backend && python -m pytest        # unit tests, no live credentials needed
cd frontend && pnpm run lint && pnpm run test && pnpm run build
```

Runs automatically in CI (`.github/workflows/ci.yml`) on every push/PR. See [Contributing](CONTRIBUTING.md) for what this does and doesn't cover.

## Verify stack (manual, needs live credentials)

```bash
python scripts/verify_supabase.py
python scripts/verify_rls.py      # requires backend on :8000
python scripts/verify_gee.py      # GEE credentials
python scripts/bootstrap_ml_models.py  # M4 SEN2SR + M12 ML weights
python scripts/test_e2e_flows.py
```
