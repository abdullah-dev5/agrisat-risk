# Audit Findings — Prioritized Backlog

Produced from a full-repository review (structure, backend/security, frontend/docs) on 2026-09-27. This is a **backlog**, kept current as items are fixed — a `[FIXED 2026-09-27]` tag on an item means development has landed; everything else is still open. Items are ordered by severity within each section so a future session can work top-down. Each item names the exact file(s) involved so it can be picked up without re-deriving context.

For the system-level picture these findings sit inside, see [`ARCHITECTURE.md`](ARCHITECTURE.md).

## What's already solid (for balance)

- Tenant filtering (`institution_id`) is applied consistently across every service function reviewed in `field_service.py` and `report_service.py` — no IDOR found in the reviewed code paths.
- Secrets hygiene: `.env` files and the GEE service-account JSON are correctly gitignored and confirmed never committed to git history; Docker mounts the GEE key read-only instead of baking it into the image.
- Error handling is centralized and environment-aware (`backend/app/main.py` exception handlers, `core/security.py`'s `public_error_message`) — a deliberate, working "security hardening" pattern.
- Security headers, `TrustedHostMiddleware`, CORS allowlist, and IP rate limiting on registration are all present and wired.
- `scripts/verify_rls.py` gives real, automated cross-tenant isolation testing against the live API.
- Sensible tiered satellite-data fallback design (Planet → SEN2SR → SAR) that degrades gracefully to `INSUFFICIENT_DATA` instead of hard-failing.
- Frontend: strict TypeScript config (`strict`, `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`), consistent loading/error/empty states across every async page, decent accessibility (`aria-live` regions, skip link, `aria-expanded`/`aria-controls`, labeled form fields), and frontend/backend timeout budgets that are actually matched to the async GEE job durations.

## Critical / High

1. **No automated test suite and no CI pipeline anywhere in the repo.**
   No `pytest` suite, no `backend/tests/`, no JS test runner, no ESLint/Prettier, no `.github/workflows`. What exists (`scripts/verify_*.py`, `test_e2e_flows.py`, `test_stack.py`) are manual, live-credential-dependent scripts, not something a PR can be gated on automatically. This is the single biggest structural gap in the project and should be scoped as its own follow-up (backend: pytest + mocked Supabase/GEE; frontend: Vitest + React Testing Library; then a GitHub Actions workflow running both plus `tsc -b`).

2. **[PARTIALLY FIXED 2026-09-27] In-memory, per-process job queue with no crash recovery.**
   `backend/app/services/job_runner.py` — a `ThreadPoolExecutor(max_workers=2)` plus an in-memory `_active: set[str]` guarded by a `Lock`. Consequences: (a) doesn't dedupe across multiple backend replicas, so horizontal scaling could run duplicate concurrent GEE jobs for the same field; (b) *(fixed)* if the process crashes mid-job, the field used to be left with `processing_status = "processing"` forever — now `reconcile_stale_processing()` runs once at startup and every `job_reconcile_interval_seconds` (default 5 min) via a daemon thread started in `main.py`'s startup hook, and marks any field stuck in `processing` past `job_stale_timeout_minutes` (default 15 min) as `failed` with a clear message, skipping anything genuinely still running in this process's own `_active` set; (c) `shutdown_executor()` still uses `cancel_futures=True`, so in-flight jobs are abruptly cancelled on shutdown — the next reconciliation sweep (on restart or after the timeout) will clean up the resulting stuck row, but there's still no immediate cleanup at shutdown time itself. **Still open:** (a) cross-replica dedupe — this fix only helps a single-process deployment recover from its own crashes; horizontal scaling still needs a durable queue (Redis/etc.) as `docs/PRODUCTION.md` already notes. Also fixed as part of this: `FieldDetailPage.tsx` previously only showed a "failed" banner if the *current session* had polled and seen `failed` — a field already `failed` on a fresh page load (exactly what the new sweep produces) showed nothing. It now also checks `detail.processing_status`/`processing_error` directly.

3. **[FIXED 2026-09-27] N+1 queries in portfolio report generation.**
   `backend/app/services/report_service.py` — `generate_portfolio_csv` and `generate_portfolio_pdf` looped over every field and issued a separate `risk_assessments` query per field. Fixed by adding `_current_assessments_by_field()`, which batches with a single `.in_("field_id", field_ids)` query (the same pattern `field_service.list_fields` already used), and both report functions now look up assessments from that batched dict instead of querying per row.

4. **`ALLOW_OPEN_REGISTRATION=true` is the shipped `.env.example` default.**
   `backend/.env.example:30` — anyone can self-register a new institution + admin account unless this is explicitly overridden. `docs/PRODUCTION.md` already documents the correct production value (`false`) — the gap is that the *example* default doesn't nudge toward it, and there's no runtime warning if a production-flagged deployment still has it on. Confirm every real deployment sets this to `false` after first-institution bootstrap; consider a startup-time warning log when `APP_ENV=production` and `ALLOW_OPEN_REGISTRATION=true`.

5. **[FIXED 2026-09-27] `/health/gee` leaks raw exception text to unauthenticated callers, in every environment.**
   `gee_health_probe()` still returns the raw message internally (it's `lru_cache`d and other internal callers may want detail), but the `/health/gee` route (`backend/app/api/routes/health.py`) now copies the result and replaces `message` with `"error"` (logging the real message server-side instead) whenever `connection == "error"` and detail isn't enabled — the same `_detail_enabled()` gate `/health/supabase` already used.

6. **Two docs contradicted current behavior** — now fixed as part of this pass, listed here for traceability: `docs/SRS-traceability.md` referenced the removed `demo_data.py` synthetic fallback, and `docs/UI-UX-INSPIRATION.md` said the M9 redesign was "blocked" though it shipped. Keep an eye out for the same drift in `docs/ARCHITECTURE.md`/`CHANGELOG.md` as the code changes further.

7. **[FIXED 2026-09-27] Frontend: unhandled promise rejection risk in `useAuth`.**
   `frontend/src/hooks/useAuth.ts` — `sb.auth.getSession().then(...)` had no `.catch()`. Fixed by chaining `.catch(() => { setUser(null); setLoading(false); })` so a rejected session check no longer leaves `LoadingScreen` hanging.

## Medium

8. **[FIXED 2026-09-27] Silent polling failure in `useFieldProcessing`.**
   `frontend/src/hooks/useFieldProcessing.ts` — the poll `catch` block just called `setPolling(false)` with no error surfaced. Fixed: the hook now exposes a `pollError` state (set on a failed poll request, cleared on the next successful one or when polling restarts), and `FieldDetailPage.tsx` renders it as an inline error message when analysis isn't otherwise in progress.

9. **Registration flow duplicate-submission edge case.**
   `frontend/src/pages/RegisterFieldPage.tsx` — `handleSubmit` creates the field via `api.createField()` and only afterward awaits `waitForFieldProcessing` (up to 6 minutes). If that wait times out or the connection drops, the shown error is generic, but the field record already exists server-side. The user has no way from that screen to know it was created, and may resubmit and create a duplicate field. Fix: on timeout, surface the created field's ID/link instead of a bare error, or check for an existing field with matching boundary/name before allowing resubmission.

10. **GEE health probe cached forever.**
    `backend/app/services/tiers/gee_client.py:73` — `@lru_cache(maxsize=1)` on `gee_health_probe()` means `/health/gee` reports the *first-ever* result (success or failure) for the lifetime of the process, not a live check. Fix: cache with a short TTL (e.g. re-probe if older than 60s) instead of unconditionally forever.

11. **No retry/backoff for transient GEE failures.**
    Nothing in `backend/app/services/tiers/gee_client.py` retries a timed-out or rate-limited GEE call — a single transient failure fails the whole tier fetch for that job. Low effort, meaningful reliability win: wrap GEE calls with a small bounded retry (e.g. 2 retries, exponential backoff) for known-transient error types.

12. **Shallow input validation in `backend/app/schemas/domain.py`.**
    - **[FIXED 2026-09-27]** `admin_email`, `contact_email`, and `InviteUserRequest.email` were plain `str` — switched to Pydantic's `EmailStr` (added `email-validator` to `backend/requirements.txt` and installed it, since `EmailStr` requires it at import time). Malformed emails are now rejected with a 422 at the API layer instead of reaching Supabase Auth first.
    - **Still open:** `crop_type: str = "wheat"` (line 49) / `crop_type: str | None` (line 58) / `crop_type: str` (line 71) are still free text with no enum/whitelist, even though the risk/baseline pipeline is effectively hard-coded to the pilot crop (`settings.pilot_crop`). A mismatched value doesn't crash (handled as `INSUFFICIENT_DATA` in `risk_engine.py:100-114`) but is a silent data-quality trap. Left open deliberately — constraining this to an enum is a product decision (which crops does the baseline engine actually support?) more than a pure bug fix.
    - **Still open:** `boundary_geojson: dict[str, Any]` is validated only via `shapely.shape()` plus a geometry-type check (`backend/app/services/geometry.py:12-16`); invalid polygons are silently "fixed" via `geom.buffer(0)` (`geometry.py:36`) rather than rejected, which can mask genuinely malformed client input, and there's no vertex-count/coordinate-precision cap before it reaches `compute_area_hectares`/GEE `reduceRegion` (minor DoS surface via a pathological polygon).

13. **Latent IDOR trap in `process_field`.**
    `backend/app/services/field_service.py:345` — `process_field(field_id, settings)` takes only `field_id`, with no `institution_id` check of its own (confirmed: the function loads the field by ID alone, lines 346-351). Safe *today* only because every current caller (`create_field`, `update_field`, `request_reprocess`) validates ownership before calling `enqueue_field_processing`. If a future code path ever calls `enqueue_field_processing`/`process_field` with an unvalidated `field_id`, there is no ownership check at that layer to catch it. Fix: either accept and check `institution_id` inside `process_field` itself, or add a comment at the function boundary making the caller contract explicit.

14. **Migration process is fragile.**
    `supabase/migrations/001`–`006` are hand-numbered plain SQL files with no migration framework (Alembic/Flyway-equivalent), no down-migrations, and no migration-ledger table visible in the schema. Workable at 6 migrations; will get harder to reason about as the schema grows. Consider adopting Supabase's own migration tracking conventions more strictly, or a lightweight ledger table, before the next few migrations land.

15. **Duplicated error handling / double logging in `get_field_imagery`.**
    `backend/app/services/field_service.py:498-508` has its own bespoke try/except → 502 logic that duplicates what the global exception handlers in `main.py` already do, and logs the error twice (`logger.exception` + `logger.error`). Low-risk cleanup: remove the local handler and let it bubble to the shared handler.

## Low / cleanup

16. **Frontend dead code.** `frontend/src/lib/constants.ts` exports `MAP_TILE_URL`/`MAP_ATTRIBUTION` (a CARTO street-tile config) that's no longer imported anywhere — `mapBasemaps.ts`'s `BASEMAPS` array has its own equivalent `street` entry. Leftover from before the multi-basemap refactor.
17. **Vestigial empty directories.** `frontend/src/mock/` and `frontend/src/mock/data/` exist on disk (untracked) — the demo-data-removal commit deleted the files but not the folders.
18. **Dead tsconfig stub.** `frontend/tsconfig.app.json` is a near-empty stub referencing `tsconfig.json`, but `tsconfig.json` already contains the full compiler options directly and isn't set up with `composite`/project references — `tsconfig.app.json` appears unused.
19. **No ESLint/Prettier configuration** for the frontend despite the strict TypeScript setup — nothing enforces style/lint rules today beyond the compiler itself.
20. **Duplicate list+table DOM.** `FieldsListPage`/`DashboardPage` render both a card list and a full `<table>` for the same data, toggled via CSS `display:none` media queries (`index.css` ~lines 354-364) rather than conditional rendering. Not an accessibility bug (hidden content is excluded from the a11y tree) but it's duplicate markup a leaner implementation could avoid.
21. **One-row-at-a-time baseline inserts.** `backend/app/services/baseline.py:178-185` inserts baseline rows in a loop with a per-row try/except for unique-constraint violations, rather than a single bulk insert. Baseline builds are infrequent (offline, per `docs/PRODUCTION.md`), so impact is low.
22. **`VegetationChart` recomputes derived data every render** without memoization (`chartData`/`nearestBaseline`) — given realistic per-field time-series sizes (a season of readings), unlikely to matter in practice; worth a `useMemo` pass only if profiling ever shows it matters.
23. **README said "React 18"** while `frontend/package.json` pins `react@^19.0.0` — fixed in this pass; watch for the same drift on future dependency bumps.

## Suggested order of attack

1. ✅ Ship the docs refresh (this pass) so the backlog above is visible and the two contradicted docs stop misleading readers.
2. ✅ Land the small, low-risk fixes: #7 (`useAuth` `.catch()`), #5 (`/health/gee` sanitization), #3 (N+1 batching in `report_service.py`), #8 (surface polling errors), #12's `EmailStr` tightening. `crop_type`/boundary validation in #12 stayed open (product decision, not a pure bug).
3. ✅ Reconciliation sweep for stuck `processing` fields (#2, single-process crash recovery) — cross-replica dedupe for horizontal scaling stays open.
4. **Next up:** scope and build the automated test suite + CI pipeline (#1) as its own dedicated effort — it's large enough to deserve its own plan rather than being folded into incremental fixes.
5. Cleanup items (#16-23) whenever convenient; they carry no urgency.
