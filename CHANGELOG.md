# Changelog

Notable changes to AgriSat Risk, grouped by milestone. Format loosely follows [Keep a Changelog](https://keepachangelog.com/); dates are commit dates on `main`.

## Unreleased — Documentation refresh, full audit-backlog closure, test suite + CI, live E2E testing

- Added `docs/ARCHITECTURE.md`, `docs/AUDIT-FINDINGS.md`, `docs/FEATURE-ROADMAP.md`, `docs/FREE-VS-PAID-RESOURCES.md`, `docs/USER-FLOW.md`, `docs/WALKTHROUGH.md`, `CONTRIBUTING.md`; corrected stale references in `README.md`, `docs/SRS-traceability.md`, `docs/UI-UX-INSPIRATION.md`.
- Added a real backend test suite (pytest, `backend/tests/`), a frontend unit test suite (Vitest + React Testing Library), ESLint + Prettier, and a GitHub Actions CI pipeline running all of it on every push/PR — closing the single biggest structural gap identified in the audit.
- Added a live end-to-end test suite (Playwright, `frontend/e2e/`) that runs against the real stack (Supabase + Google Earth Engine) — not mocks. It found four real bugs that neither code review nor the mocked test suite could have caught:
  - **JWT verification rejected every login under minor clock skew** — `jwt_verify.py` had zero leeway on the `iat` claim, so any deployment with even small clock drift would reject every single login. Fixed with a 30s leeway.
  - **`RegisterInstitutionPage`/`LoginPage` inputs had no accessible label** — `<label>`/`<input>` pairs weren't connected via `htmlFor`/`id`, a real screen-reader gap on the two account-entry screens. Fixed.
  - **The "Street" basemap silently served "API KEY REQUIRED" watermark tiles** — CARTO's free anonymous tile service now gates tiles behind a key, returning HTTP 200 with a watermarked image rather than an error, so nothing in the app would ever catch it except looking at the rendered map. Switched to Esri's free `Canvas/World_Light_Gray_Base` (same provider already used elsewhere in the app).
  - **The "Hybrid" basemap registered as two duplicate entries in the layer switcher** — two sibling `TileLayer`s under one `LayersControl.BaseLayer` register as two separate control entries in react-leaflet. Fixed by grouping them so they toggle together as one layer.
- Added a new "Map" basemap (Esri `World_Street_Map`, free, no key) with legible town/village names, roads, and landmarks — for identifying where a field actually is, distinct from the existing minimal "Street" overview layer.
- Cleaned up the map layer switcher's styling — it was unintentionally inheriting the site-wide uppercase/letter-spaced form-label style from Leaflet's own internal `<label>` markup, making it look like an oversized shouty block list; now a compact, normal-case menu. Also made the map status banner (the dark-green "boundary closed"/draw-hint message) dismissible with a close button, since it can sit over parts of the map a user wants to see.
- Fixed blurry live field imagery (`gee_imagery.py`): sampling Sentinel-2's ~10m visible bands directly for a typical field produced arrays as small as a few dozen pixels per side, stretched by the browser to fill the display. Now resamples server-side (bicubic, in GEE) to a scale chosen from the field's own footprint, applies a per-band contrast stretch to the scene's actual reflectance range (replacing one fixed window that looked over/under-exposed depending on scene content), and finishes with a light sharpening pass — all display-quality processing on the real sampled pixels, not a learned reconstruction. Also removed a redundant duplicate GEE sample per scene along the way.
- Fixed essentially every other item in `docs/AUDIT-FINDINGS.md` that was fixable by editing code: N+1 queries in portfolio report generation, the in-memory job queue's crash recovery (a reconciliation sweep for stuck `processing` fields), a latent IDOR trap in `process_field`, GEE health-check caching/retry behavior, unauthenticated info-disclosure on `/health/gee`, several frontend UX/reliability gaps, and a round of dead-code cleanup. See the doc for the full, itemized list — what's left open is explicitly a process/product decision, not an oversight.
- Confirmed as an explicit, correct-for-now decision: Google Earth Engine's noncommercial tier is appropriate while AgriSat has no paying institution and is operating as research/development — revisit before any commercial launch (see `docs/FREE-VS-PAID-RESOURCES.md`).

## 2026-07-01 — Production hardening, M4 SEN2SR, M12 ML

- Async GEE field processing made production-ready (background job queue, `/fields/{id}/processing` polling).
- M4 Tier 2 pipeline: local SEN2SR super-resolution model over GEE reflectance patches, with a GEE weekly-composite fallback.
- M12 ML risk layer: gradient-boosted classifier that can elevate (never downgrade) the z-score-based risk tier.
- Security hardening: security headers middleware, trusted-host/CORS allowlists, environment-aware error sanitization, registration rate limiting.

_(`fcb439e`)_

## 2026-06-30 — MVP modules complete, tenant isolation, Guide page

- Completed remaining MVP modules; live GEE-generated field imagery (RGB/NDVI previews).
- Multi-tenant isolation: application-level `institution_id` filtering across all field/report queries, backed by Postgres RLS policies.
- In-app Guide page (`/guide`) — plain-language and technical documentation, linked from the dashboard.
- **Removed the synthetic/demo-data fallback** — Tier 3 vegetation analysis now requires a live GEE connection; there is no local-development stand-in.

_(`6956b19`, `6c15fd3`, `c96ef71`)_

## 2026-06-29 — Live GEE Tier 3 pipeline

- M3 Tier 3 pipeline: Sentinel-1 SAR + Sentinel-2 optical + CHIRPS rainfall via Google Earth Engine, wired end-to-end and made the always-available baseline tier.
- Satellite basemaps and pipeline-status visibility in the map UI.
- Live Supabase integration, Matiari pilot district defaults, interactive field-boundary drawing tools.

_(`f0052e9`, `380314b`)_

## 2026-06-28 — Canopy design system

- Migrated frontend tooling to pnpm.
- Adopted the "Canopy" design system for the dashboard (M9): map-first layout, WCAG AA risk colors, mobile navigation.

_(`b20f435`)_

## 2026-06-27 — Initial scaffold

- Project foundation: repo structure, Supabase/PostGIS schema and migrations, module-plan documentation (M0).
- FastAPI backend scaffold: tier adapters, fusion, risk engine, report generation.
- React dashboard scaffold: field registration, map, risk visualization.
- Supabase setup guide, geometry RPC helpers, connectivity checks (M11).

_(`81da47d`, `944dff0`, `c6ba6da`)_

---

For unreleased/in-progress work and known gaps, see [`docs/AUDIT-FINDINGS.md`](docs/AUDIT-FINDINGS.md).
