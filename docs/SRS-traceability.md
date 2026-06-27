# SRS v2.0 → Implementation Traceability

| SRS Requirement | Implementation |
|---|---|
| FR-1.1–1.4 | `auth_routes.py`, `profiles` table, RLS policies |
| FR-2.1–2.6 | `RegisterFieldPage.tsx`, `geometry.py`, `field_service.py` |
| FR-3.1–3.9 | `services/tiers/*`, `fusion.py`, `vegetation_readings` table |
| FR-3.7 | Tier 3 demo/GEE path always runs; Tier 1/2 optional |
| FR-4.1–4.3 | `baseline.py`, `baseline_stats` table |
| FR-5.1–5.4 | `risk_engine.py`, `risk_assessments`, `risk_audit_log` |
| FR-6.1–6.4 | `DashboardPage`, `FieldDetailPage`, `FieldsMap`, `VegetationChart` |
| FR-7.1–7.2 | `report_service.py`, PDF/CSV endpoints |
| NFR-4 | Supabase Auth JWT + RLS institution isolation |
| NFR-6 | Disclaimers in UI + risk explanations |
| NFR-7 | Separate tier adapters, fusion, API, frontend layers |

**Pilot defaults:** wheat · Faisalabad District (`config.py`, `constants.ts`)

**Demo mode:** Without GEE/Planet credentials, Tier 3 uses synthetic readings (`demo_data.py`) so the full UI flow is testable locally.
