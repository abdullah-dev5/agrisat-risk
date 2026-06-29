# Google Earth Engine (Tier 3 — Sentinel-1/2 + CHIRPS)

Enable live satellite vegetation extraction for Matiari wheat fields.

## 1. Create a Google Cloud project

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project (note the **Project ID**)

## 2. Enable Earth Engine

1. Go to [Earth Engine](https://console.cloud.google.com/earth-engine)
2. Register the project for **Earth Engine access** (commercial/non-commercial per your use case)
3. Wait for approval if required on new accounts

## 3. Service account

1. **IAM & Admin → Service Accounts → Create**
2. Name: `agrisat-gee` (any name)
3. Grant role: **Earth Engine Resource Viewer** (or Earth Engine User)
4. **Keys → Add key → JSON** — download the file
5. Save as `backend/gee-service-account.json` (gitignored — never commit)

## 4. Register service account with Earth Engine

```bash
# Install earthengine CLI once
pip install earthengine-api

# Authenticate as yourself (one-time, for registration only)
earthengine authenticate

# Register the service account (replace email and project)
earthengine register --email your-sa@project.iam.gserviceaccount.com --project your-gcp-project-id
```

Or use the [Earth Engine access page](https://signup.earthengine.google.com/) to add the service account.

## 5. Backend `.env`

```env
GEE_SERVICE_ACCOUNT_EMAIL=your-sa@project.iam.gserviceaccount.com
GEE_PRIVATE_KEY_PATH=./gee-service-account.json
GEE_PROJECT=your-gcp-project-id
GEE_ALLOW_DEMO_FALLBACK=true
```

| Variable | Description |
|----------|-------------|
| `GEE_SERVICE_ACCOUNT_EMAIL` | Service account email |
| `GEE_PRIVATE_KEY_PATH` | Path to JSON key file |
| `GEE_PROJECT` | GCP project ID (required for newer EE API) |
| `GEE_ALLOW_DEMO_FALLBACK` | `true` = use synthetic data if GEE fails; `false` = hard fail |

## 6. Install dependency

```bash
cd backend
pip install -r requirements.txt
```

`earthengine-api` is included in `requirements.txt`.

## 7. Verify

```bash
python scripts/verify_gee.py
```

With backend running:

```bash
curl http://localhost:8000/health/gee
```

Expected when configured:

```json
{
  "configured": true,
  "initialized": true,
  "connection": "ok",
  "message": "S2 collection reachable (...)"
}
```

## 8. What GEE powers (M3)

| Dataset | Use |
|---------|-----|
| `COPERNICUS/S2_SR_HARMONIZED` | NDVI + EVI per field AOI |
| `COPERNICUS/S1_GRD` | VV backscatter (cloud-penetrating) |
| `UCSB-CHG/CHIRPS/DAILY` | Rainfall anomaly for risk flags |

On each **Register field** or **Reprocess**, the backend:

1. Extracts zonal stats inside the field polygon
2. Fuses Tier 3 readings into the vegetation time-series
3. Stores pipeline source in `risk_audit_log` (`gee_live` vs `demo_fallback`)

## Troubleshooting

| Error | Fix |
|-------|-----|
| `GEE credentials not configured` | Set `.env` vars and restart uvicorn |
| `Invalid JSON` / key path | Check `GEE_PRIVATE_KEY_PATH` relative to `backend/` cwd |
| `User does not have permission` | Register SA with Earth Engine; check IAM roles |
| `No scenes found` | Sowing date too recent or AOI outside coverage — try Matiari bounds |
| Demo data still showing | Check `/health/gee` — `connection` must be `ok` |

## Field detail UI

When live GEE is active, field detail shows **Latest acquisition** dates from real scenes and audit log `vegetation_source: gee_live`.
