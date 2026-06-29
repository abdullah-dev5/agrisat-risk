# Google Earth Engine — Exact Setup Guide (AgriSat M3)

**Time:** ~30–45 minutes (plus Google approval wait if new)  
**Platform:** Windows · **Pilot:** Matiari District · **Stack:** AgriSat backend (`e:\AgriSat`)

This guide wires **live** Sentinel-1/2 + CHIRPS data. Without it, the app uses **demo** vegetation (labeled in the UI).

---

## What you are setting up

| Piece | Purpose |
|-------|---------|
| Google Cloud **project** | Billing + Earth Engine container |
| **Earth Engine** on that project | Access to satellite collections |
| **Service account** + JSON key | Backend authenticates as this user |
| **`backend/.env`** | Tells AgriSat where the key is |
| **`earthengine-api`** Python package | Our code talks to GEE |

AgriSat uses the **Python Client Library** (`ee` package) only — **not** the Code Editor or REST API directly.

---

## Prerequisites

- Google account
- AgriSat repo cloned at `e:\AgriSat`
- Python 3.10+ installed
- Backend already works with Supabase (`python scripts/test_stack.py` passes)

---

## Step 1 — Create a Google Cloud project

1. Open: https://console.cloud.google.com/projectcreate
2. **Project name:** `AgriSat Risk` (any name)
3. Click **Create**
4. After creation, open: https://console.cloud.google.com/home/dashboard
5. At the top, note the **Project ID** (not the display name)  
   Example: `agrisat-risk-123456`  
   → You will use this as `GEE_PROJECT`

---

## Step 2 — Enable Earth Engine on the project

1. Open: https://console.cloud.google.com/earth-engine
2. Select your project (top bar) if prompted
3. Click **Register** / **Enable Earth Engine** (wording varies)
4. Choose use type:
   - **Noncommercial** — research / NGO / education
   - **Commercial** — lenders / insurers (likely your case)
5. Complete the form and submit
6. **Wait for approval** if Google shows “pending” (can take hours to a few days)

**Check it worked:** https://code.earthengine.google.com/ opens and lets you pick your project.

---

## Step 3 — Enable required APIs (recommended)

1. Open: https://console.cloud.google.com/apis/library
2. Ensure project is selected
3. Search and **Enable** each:
   - **Earth Engine API**
   - **Cloud Resource Manager API** (often auto-enabled)

---

## Step 4 — Create a service account

1. Open: https://console.cloud.google.com/iam-admin/serviceaccounts
2. Click **+ Create service account**
3. Fill in:
   - **Name:** `agrisat-gee`
   - **ID:** `agrisat-gee` (auto-filled)
4. Click **Create and continue**
5. **Grant roles** — add **all** of these:
   - `Earth Engine Resource Viewer` (or `Earth Engine User`)
   - **`Service Usage Consumer`** (`roles/serviceusage.serviceUsageConsumer`) — **required** for API access
6. Click **Continue** → **Done**

7. Click the new service account email (e.g. `agrisat-gee@agrisat-risk-123456.iam.gserviceaccount.com`)
8. Tab **Keys** → **Add key** → **Create new key** → **JSON** → **Create**
9. A `.json` file downloads — **keep it secret**

---

## Step 5 — Place the key file in AgriSat

1. Move/rename the downloaded file to:

   ```
   e:\AgriSat\backend\gee-service-account.json
   ```

2. Confirm it is **not** committed to git (already in `.gitignore`)

3. Open the JSON and copy the **`client_email`** field — you need it for `.env`  
   Example: `"client_email": "agrisat-gee@agrisat-risk-123456.iam.gserviceaccount.com"`

---

## Step 6 — Register the service account with Earth Engine

The service account must be allowed to use Earth Engine (separate from IAM).

### Option A — Command line (recommended)

Open **PowerShell**:

```powershell
cd e:\AgriSat\backend
pip install earthengine-api
```

**One-time:** authenticate as **yourself** (human Google account) to run registration:

```powershell
earthengine authenticate
```

- A browser opens → sign in with the same Google account that owns the GCP project
- Allow access → return to terminal

**Register the service account** (replace with your values):

```powershell
earthengine register --email agrisat-gee@agrisat-risk-123456.iam.gserviceaccount.com --project agrisat-risk-123456
```

Expected: success message or confirmation that the SA is registered.

### Option B — Earth Engine signup page

1. Open: https://signup.earthengine.google.com/
2. Follow prompts to link your GCP project and service accounts (if offered)

---

## Step 7 — Configure `backend/.env`

Edit `e:\AgriSat\backend\.env` and add/update these lines (keep existing Supabase vars):

```env
# Google Earth Engine (Tier 3)
GEE_SERVICE_ACCOUNT_EMAIL=agrisat-gee@agrisat-risk-123456.iam.gserviceaccount.com
GEE_PRIVATE_KEY_PATH=./gee-service-account.json
GEE_PROJECT=agrisat-risk-123456
GEE_ALLOW_DEMO_FALLBACK=true
```

| Variable | Exact value |
|----------|-------------|
| `GEE_SERVICE_ACCOUNT_EMAIL` | `client_email` from the JSON key file |
| `GEE_PRIVATE_KEY_PATH` | `./gee-service-account.json` (relative to `backend/` when you run uvicorn) |
| `GEE_PROJECT` | GCP **Project ID** from Step 1 |
| `GEE_ALLOW_DEMO_FALLBACK` | `true` = fall back to demo if GEE fails; `false` = hard error |

**Important:** Start the backend from `e:\AgriSat\backend` so the key path resolves correctly:

```powershell
cd e:\AgriSat\backend
python -m uvicorn app.main:app --reload --port 8000
```

---

## Step 8 — Install Python dependencies

```powershell
cd e:\AgriSat\backend
pip install -r requirements.txt
```

This installs `earthengine-api` (listed in `requirements.txt`).

---

## Step 9 — Verify GEE (command line)

From repo root:

```powershell
cd e:\AgriSat
python scripts\verify_gee.py
```

**Success looks like:**

```
=== AgriSat GEE verification ===

configured:  True
connection:  ok
message:     S2 collection reachable (N scenes in probe window)

OK: GEE Tier 3 pipeline ready
```

**If you see `SKIP: GEE not configured`** → Step 7 `.env` vars missing or typo.

**If `connection: error`** → see Troubleshooting below.

---

## Step 10 — Verify via backend health endpoint

1. Start backend (if not running):

   ```powershell
   cd e:\AgriSat\backend
   python -m uvicorn app.main:app --reload --port 8000
   ```

2. In another terminal or browser:

   ```
   http://localhost:8000/health/gee
   ```

**Success JSON:**

```json
{
  "configured": true,
  "initialized": true,
  "connection": "ok",
  "message": "S2 collection reachable (...)"
}
```

---

## Step 11 — End-to-end test in AgriSat UI

1. Start frontend:

   ```powershell
   cd e:\AgriSat\frontend
   pnpm dev
   ```

2. Log in → **Register field** (or open an existing field)
3. Draw a small polygon in **Matiari** on the **Satellite** basemap (zoom 16+)
4. Use sowing date at least **2–3 months ago** (e.g. `2025-11-15`) so Sentinel scenes exist
5. Submit **Register & analyze**
6. Open field detail page

**Live GEE working when you see:**

- Text: **“Data pipeline: Live GEE · Sentinel-1/2”**
- Vegetation chart with real acquisition dates (not perfectly regular 5-day demo spacing)
- Map label includes latest acquisition date

**Still demo when you see:**

- **“Demo pipeline (configure GEE for live data)”**

---

## Quick reference — file checklist

```
e:\AgriSat\
├── backend\
│   ├── .env                          ← GEE_* variables set
│   ├── gee-service-account.json      ← downloaded key (secret)
│   └── requirements.txt              ← includes earthengine-api
├── docs\
│   └── GEE-SETUP.md                  ← this file
└── scripts\
    └── verify_gee.py                 ← run to test
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `GEE credentials not configured` | Add all four `GEE_*` vars to `backend/.env`; restart uvicorn |
| `FileNotFoundError` for JSON key | Key must be at `backend/gee-service-account.json`; run uvicorn from `backend/` |
| `Invalid grant` / `invalid_client` | Wrong key file or email; re-download key; match `GEE_SERVICE_ACCOUNT_EMAIL` to `client_email` |
| `Earth Engine client library not initialized` | Set `GEE_PROJECT` to Project ID; run `earthengine register` again |
| `User does not have permission` | SA not registered with EE; add IAM role **Earth Engine Resource Viewer** |
| `Caller does not have required permission to use project` | IAM → service account → add **Service Usage Consumer** + **Earth Engine Resource Viewer** → wait 2–5 min |
| `Caller does not have required permission` | Earth Engine not enabled on project; wait for approval |
| `No Sentinel scenes found` | Sowing date too recent; move AOI inside Matiari; widen date range |
| `/health/gee` ok but UI still “Demo” | Re-register or **reprocess** field after GEE was configured (old fields used demo) |
| `earthengine: command not found` | Use `python -m earthengine authenticate` or ensure Scripts folder is on PATH |

### Reprocess an existing field (after GEE setup)

```http
POST http://localhost:8000/api/v1/fields/{field_id}/reprocess
Authorization: Bearer <your_supabase_jwt>
```

Or register a **new** field.

---

## What AgriSat pulls from GEE

| Collection | Product |
|------------|---------|
| `COPERNICUS/S2_SR_HARMONIZED` | NDVI + EVI (10 m, cloud-filtered) |
| `COPERNICUS/S1_GRD` | VV SAR backscatter (all-weather) |
| `UCSB-CHG/CHIRPS/DAILY` | Rainfall mm + anomaly vs prior years |

Code: `backend/app/services/tiers/gee_client.py`

---

## Security

- **Never** commit `gee-service-account.json` or paste keys in chat/PRs
- Rotate keys if exposed: GCP Console → Service account → Keys → delete old → create new
- Production: store key in a secret manager; set `GEE_PRIVATE_KEY_PATH` or mount as env

---

## Need help?

If stuck, share (redact secrets):

1. Output of `python scripts\verify_gee.py`
2. JSON from `http://localhost:8000/health/gee` (no keys)
3. Whether Earth Engine approval is still pending in GCP Console
