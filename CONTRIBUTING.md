# Contributing

## Dev setup

Prerequisites: Node.js 20+, pnpm 9+ (`npm install -g pnpm`), Python 3.11+, a Supabase project, a Google Earth Engine service account.

```bash
# 1. Supabase — create a project, then run migrations
supabase db push
# or paste supabase/migrations/*.sql (001 through 006, in order) into the SQL editor

# 2. Copy env templates and fill in real values
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# 3. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows; source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev   # http://localhost:5173, proxies /api and /health to :8000
```

See [`docs/SUPABASE-SETUP.md`](docs/SUPABASE-SETUP.md) and [`docs/GEE-SETUP.md`](docs/GEE-SETUP.md) for the two external services in detail.

## Branching and commits

Full conventions live in [`docs/GIT-WORKFLOW.md`](docs/GIT-WORKFLOW.md). Summary:

- `main` is always deployable/demo-ready.
- Feature branches: `feat/m{N}-{short-name}` (module work) or `fix/{short-description}` / `chore/{short-name}` otherwise.
- Commit format: `<type>(<scope>): <short summary>`, types `feat`/`fix`/`chore`/`docs`/`refactor`/`test`.

## Automated checks (CI)

`.github/workflows/ci.yml` runs on every push to `main` and every PR:

- **Backend:** `cd backend && pip install -r requirements-dev.txt && python -m pytest` — unit tests in `backend/tests/` over pure-logic modules (risk scoring, geometry, security helpers) plus mocked-Supabase tests for the reconciliation sweep and the report-generation batching fix. No live Supabase/GEE credentials needed or used.
- **Frontend:** `pnpm install --frozen-lockfile`, then `pnpm run lint` (ESLint), `pnpm run test` (Vitest + React Testing Library — boundary parsing, map-status logic, `RiskBadge`), then `pnpm run build` (`tsc -b && vite build`).

Run the same commands locally before pushing:

```bash
cd backend && python -m pytest
cd frontend && pnpm run lint && pnpm run test && pnpm run build
```

`pnpm run format` / `pnpm run format:check` (Prettier) exist but aren't run in CI yet — the existing codebase predates Prettier and hasn't been reformatted, so `format:check` would fail on unrelated pre-existing style, not a real regression. Run `pnpm run format` deliberately, as its own commit, if you want to adopt it.

## What CI does *not* cover — still needs the manual scripts

CI tests logic in isolation, not integration with real Supabase/GEE. For anything touching those paths, still run the relevant scripts by hand against a real (dev/staging) setup before opening a PR:

```bash
python scripts/verify_supabase.py    # DB connectivity + schema sanity
python scripts/verify_rls.py         # cross-tenant isolation — run this if you touched any field/report/auth code; requires backend on :8000
python scripts/verify_gee.py         # GEE credentials reachable
python scripts/bootstrap_ml_models.py  # SEN2SR (M4) + ML risk (M12) model weights present
python scripts/test_e2e_flows.py     # end-to-end: Supabase Auth → backend API → DB
python scripts/test_stack.py         # general stack smoke test
```

## Before you touch tenant-scoped data access

Every backend query against `fields`, `risk_assessments`, or other tenant-scoped tables must filter by `institution_id` explicitly — the backend uses Supabase's service-role key, which bypasses Postgres RLS, so there is no second layer of defense against a missing filter. See [`docs/ARCHITECTURE.md#tenant-isolation`](docs/ARCHITECTURE.md#tenant-isolation) before adding a new service function that reads or writes field data, and run `scripts/verify_rls.py` afterward.
