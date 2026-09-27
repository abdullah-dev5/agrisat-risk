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

## There is no CI yet — run these manually before opening a PR

The project currently has **no automated test suite and no CI pipeline** (tracked in [`docs/AUDIT-FINDINGS.md`](docs/AUDIT-FINDINGS.md) as the top backlog item). Until that changes, these scripts are the manual gate — run whichever apply to your change against a real (dev/staging) Supabase + GEE setup:

```bash
python scripts/verify_supabase.py    # DB connectivity + schema sanity
python scripts/verify_rls.py         # cross-tenant isolation — run this if you touched any field/report/auth code; requires backend on :8000
python scripts/verify_gee.py         # GEE credentials reachable
python scripts/bootstrap_ml_models.py  # SEN2SR (M4) + ML risk (M12) model weights present
python scripts/test_e2e_flows.py     # end-to-end: Supabase Auth → backend API → DB
python scripts/test_stack.py         # general stack smoke test
```

For frontend changes, there's no lint/test script (`frontend/package.json` only has `dev`/`build`/`preview`) — at minimum run `pnpm build` to catch TypeScript errors (`tsconfig.json` is strict) before opening a PR.

## Before you touch tenant-scoped data access

Every backend query against `fields`, `risk_assessments`, or other tenant-scoped tables must filter by `institution_id` explicitly — the backend uses Supabase's service-role key, which bypasses Postgres RLS, so there is no second layer of defense against a missing filter. See [`docs/ARCHITECTURE.md#tenant-isolation`](docs/ARCHITECTURE.md#tenant-isolation) before adding a new service function that reads or writes field data, and run `scripts/verify_rls.py` afterward.
