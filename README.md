# AgriSat Risk

Satellite-based parametric crop risk platform for agricultural lenders and insurers in Pakistan.

**MVP scope:** Wheat monitoring in Matiari District, Sindh — decision-support only (not automated payout).

## Architecture

```
frontend/     React 18 + TypeScript + Leaflet dashboard (pnpm)
backend/      Python FastAPI — tier adapters, fusion, risk scoring
supabase/     PostgreSQL + PostGIS, Auth, RLS, report storage
```

### Three-tier data stack (FR-3.4)

| Tier | Source | Role |
|------|--------|------|
| 1 | PlanetScope (E&R Program) | 3m optical — preferred when approved |
| 2 | SEN2SR + Sentinel-2 | 2.5m optical fallback |
| 3 | Sentinel-1 SAR + Sentinel-2 + CHIRPS | Always-available cloud-independent baseline |

Core risk flagging works on Tier 3 alone (FR-3.7).

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

- [Module plan](docs/MODULE-PLAN.md) — delivery order and acceptance criteria (MVP complete)
- [Supabase setup](docs/SUPABASE-SETUP.md) — **start here after clone (M11)**
- [GEE setup](docs/GEE-SETUP.md) — Google Earth Engine service account
- [Git workflow](docs/GIT-WORKFLOW.md) — branch and commit conventions
- [SRS traceability](docs/SRS-traceability.md) — requirement → code map
- **In-app Guide** — http://localhost:5173/guide (plain-language + technical tutorials)

## Verify stack

```bash
python scripts/verify_supabase.py
python scripts/verify_rls.py      # requires backend on :8000
python scripts/verify_gee.py      # GEE credentials
python scripts/test_e2e_flows.py
```
