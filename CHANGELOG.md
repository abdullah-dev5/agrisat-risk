# Changelog

Notable changes to AgriSat Risk, grouped by milestone. Format loosely follows [Keep a Changelog](https://keepachangelog.com/); dates are commit dates on `main`.

## Unreleased — Documentation refresh + first audit-backlog fixes

- Added `docs/ARCHITECTURE.md`, `docs/AUDIT-FINDINGS.md`, `docs/FEATURE-ROADMAP.md`, `docs/FREE-VS-PAID-RESOURCES.md`, `docs/USER-FLOW.md`, `CONTRIBUTING.md`; corrected stale references in `README.md`, `docs/SRS-traceability.md`, `docs/UI-UX-INSPIRATION.md`.
- Fixed: N+1 queries in portfolio CSV/PDF generation (`report_service.py`), unauthenticated info-disclosure on `/health/gee`, unhandled promise rejection in `useAuth`, silent polling failures in `useFieldProcessing` (now surfaced on `FieldDetailPage`), and missing email format validation on registration/invite endpoints (`EmailStr`).
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
