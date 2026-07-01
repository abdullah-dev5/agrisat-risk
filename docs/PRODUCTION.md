# Production deployment guide

## Architecture (production)

```
Browser → CDN/static (Vite build) → API (FastAPI + Gunicorn)
                                      ↓
                              Thread pool (GEE jobs, max 2)
                                      ↓
                              Supabase (Postgres + Auth + RLS)
                                      ↓
                              Google Earth Engine
```

**Key design:** `POST /fields` and `POST /fields/{id}/reprocess` return immediately. GEE fusion runs in a background worker thread. Clients poll `GET /fields/{id}/processing`.

---

## Pre-deploy checklist

### Database
- [ ] Run migrations `001`–`006` (including `006_field_processing_status.sql`)
- [ ] Pre-build district baseline: `python scripts/build_district_baseline.py`
- [ ] Bootstrap ML weights: `python scripts/bootstrap_ml_models.py`

### Backend environment (`backend/.env`)

```env
APP_ENV=production
ALLOW_OPEN_REGISTRATION=false
REGISTRATION_SECRET=<long-random-secret-for-bootstrap-only>
HEALTH_DETAIL_ENABLED=false
BASELINE_BUILD_ON_REQUEST=false
TRUSTED_HOSTS=api.yourdomain.com,yourdomain.com
CORS_ORIGINS=https://app.yourdomain.com

SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...   # if legacy HS256

GEE_SERVICE_ACCOUNT_EMAIL=...
GEE_PRIVATE_KEY_PATH=./gee-service-account.json
GEE_PROJECT=...

ML_RISK_ENABLED=true
SEN2SR_USE_LOCAL=true
```

### Frontend (`frontend/.env`)

```env
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=...
VITE_API_URL=https://api.yourdomain.com
```

### Security
- [ ] Never commit `.env` or GEE service account JSON
- [ ] Disable open registration after first institution (`ALLOW_OPEN_REGISTRATION=false`)
- [ ] Use `X-Registration-Secret` header for controlled bootstrap signups
- [ ] Restrict `/health/*` detail routes (set `HEALTH_DETAIL_ENABLED=false`)
- [ ] TLS termination at load balancer (HSTS enabled via middleware when `https`)

---

## Run with Gunicorn

```bash
cd backend
pip install -r requirements.txt gunicorn
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 2 \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --graceful-timeout 30 \
  --keep-alive 5
```

Use **2 workers** max for GEE-heavy workloads unless you add Redis + Celery (in-memory job queue is per-process).

---

## Reverse proxy timeouts

| Route | Suggested timeout |
|-------|-------------------|
| `POST /api/v1/fields` | 30s (async enqueue) |
| `GET /api/v1/fields/*/processing` | 15s |
| `GET /api/v1/fields/*/imagery` | 180s |
| Background GEE jobs | No HTTP timeout (worker threads) |

### Nginx example

```nginx
location /api/v1/fields/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_read_timeout 180s;
}
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_read_timeout 60s;
}
```

---

## Docker

```bash
docker compose up --build
```

See `docker-compose.yml` and `backend/Dockerfile`.

---

## Performance notes

- District baseline builds are **offline only** (`BASELINE_BUILD_ON_REQUEST=false`)
- Vegetation readings use **bulk insert**
- SEN2SR + ML models are **cached in memory** per worker
- Imagery responses cached **10 minutes** per field (in-process)

For horizontal scale, move imagery cache and job queue to Redis.

---

## Verify production

```bash
python scripts/verify_supabase.py
python scripts/verify_rls.py
curl https://api.yourdomain.com/health
curl https://api.yourdomain.com/health/ml
```
