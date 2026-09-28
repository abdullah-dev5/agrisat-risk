# E2E tests (Playwright)

These run against the **real stack** — a live Supabase project (Auth + Postgres) and live Google Earth Engine — not mocks. They're a different layer from `frontend/src/**/*.test.{ts,tsx}` (Vitest unit tests, pure logic, no live services, run in CI) and `backend/tests/` (pytest, same).

## Prerequisites

1. Backend running with real credentials:
   ```bash
   cd backend && uvicorn app.main:app --port 8000
   ```
2. `frontend/.env` pointing at the same Supabase project as `backend/.env`.
3. `ALLOW_OPEN_REGISTRATION` must be enabled (it's the default in `backend/.env.example`/dev) — the walkthrough spec self-registers a fresh institution each run.

## Run

```bash
pnpm run e2e        # headless, runs everything in e2e/*.spec.ts
pnpm run e2e:ui      # Playwright's interactive UI mode, useful for debugging
```

`playwright.config.ts` will start the Vite dev server itself (`reuseExistingServer: true`, so it reuses one you already have running on :5173) — it does **not** start the backend; that has to already be running.

## What's covered

`full-walkthrough.spec.ts` — registers a brand-new institution + admin account (unique email per run, so it's safe to re-run), registers a field via GeoJSON upload, waits for the real GEE processing job to resolve, then checks the fields-list responsive layout at both desktop and mobile viewport widths (the thing behind `docs/AUDIT-FINDINGS.md` #20 — confirms the card-list/table toggle is mutually exclusive, not both visible at once).

It deliberately does **not** assert a specific risk tier or outcome for the registered field — that depends on real, variable satellite data for whatever AOI/date range the test happens to run against. What it does assert is that every step completes without crashing and that the field leaves the "processing" state within the timeout rather than getting stuck.

## Why this isn't in CI yet

CI (`.github/workflows/ci.yml`) deliberately runs with no live credentials — that was a conscious scope boundary when the pytest/Vitest suites were added (see `docs/AUDIT-FINDINGS.md` #1). Wiring this into CI would need Supabase + GEE service-account credentials added as GitHub Actions secrets, which is a real decision (whose Supabase project does CI hit — the same dev one, or a dedicated CI project?) rather than a config change. Run it locally/on demand for now; revisit CI wiring once that's decided.

## Artifacts

Screenshots land in `e2e/screenshots/`, HTML report in `playwright-report/`, traces/videos on failure in `test-results/` — all gitignored. Curated copies from a real run are checked into `docs/screenshots/walkthrough/` and shown in `docs/WALKTHROUGH.md`.

## Gotchas hit while building this

- **Windows/Git-Bash: `lsof -ti:PORT | xargs kill` can silently do nothing.** In this environment `lsof` didn't reliably find/kill the uvicorn process on :8000 — a "restarted" backend would fail to bind (`[Errno 10048] ... only one usage of each socket address`) and exit immediately, while the *original*, un-restarted process kept right on serving requests. This cost real debugging time chasing a bug that had already been fixed in source but was still running the old code. If a restart doesn't seem to change behavior, verify with `netstat -ano | grep ":8000" | grep LISTENING` and `taskkill //F //PID <pid>` instead of trusting `lsof`.
- **Test data needs a real, deliverable-looking email domain.** Pydantic's `EmailStr` (`backend/app/schemas/domain.py`) uses `email-validator`'s deliverability check, which correctly rejects RFC 2606 reserved domains (`example.com`, `.test`, `.invalid`, `.localhost`) as "special-use or reserved." Use a real domain with `+addressing` for uniqueness instead (e.g. `you+e2e-${Date.now()}@gmail.com`) — no real inbox needed, just a resolvable domain.
- **`__dirname` doesn't exist** — this project is ESM (`"type": "module"` in `package.json`). Derive it from `import.meta.url` via `fileURLToPath` when a spec needs to resolve a fixture path.
- **Assertions like `expect(locator).not.toBeVisible()` can pass trivially** if the element was never rendered in the first place, not just once it disappears after being visible. If a page has an initial loading screen, explicitly wait for *that* to clear first — otherwise a screenshot taken right after can land back on a transient loading state (e.g. a second effect run re-fetching in dev) even though the assertion technically passed.
