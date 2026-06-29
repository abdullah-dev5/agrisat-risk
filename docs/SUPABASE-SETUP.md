# Supabase Setup — AgriSat Risk (M11)

Step-by-step guide to connect your hosted Supabase project to the local backend and frontend.

---

## 1. Create a Supabase project

1. Go to [supabase.com/dashboard](https://supabase.com/dashboard) → **New project**
2. Choose a region close to Pakistan (e.g. **Singapore** or **Mumbai** if available)
3. Save your **database password** securely

---

## 2. Enable PostGIS

1. In the project: **Database → Extensions**
2. Search **postgis** → **Enable**
3. Required for field boundary polygons (FR-2.x)

---

## 3. Run migrations

**Option A — SQL Editor (simplest)**

1. Open **SQL Editor → New query**
2. Paste and run, in order:
   - `supabase/migrations/001_initial_schema.sql`
   - `supabase/migrations/002_geometry_helpers.sql`
   - (if 002 failed on `ST_AsGeoJSON`) `supabase/migrations/003_postgis_schema_fix.sql`
3. Confirm no errors

**Option B — Supabase CLI**

```powershell
cd e:\AgriSat
supabase login
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

---

## 4. Collect API keys

**Project Settings → API**

| Key | Used in |
|-----|---------|
| Project URL | `SUPABASE_URL`, `VITE_SUPABASE_URL` |
| `anon` `public` | `VITE_SUPABASE_ANON_KEY` |
| `service_role` `secret` | `SUPABASE_SERVICE_ROLE_KEY` (backend only — never expose to frontend) |
| JWT Secret | `SUPABASE_JWT_SECRET` (backend auth validation) |

---

## 5. Configure environment files

**`backend/.env`** (copy from `backend/.env.example`):

```env
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_JWT_SECRET=your-jwt-secret-from-dashboard
CORS_ORIGINS=http://localhost:5173
```

**`frontend/.env`** (copy from `frontend/.env.example`):

```env
VITE_SUPABASE_URL=https://xxxxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
VITE_API_URL=http://localhost:8000
```

---

## 6. Auth settings (recommended)

**Authentication → Providers → Email**

- Enable Email provider
- For MVP/demo: you may disable **Confirm email** so institution registration works immediately

**Authentication → URL configuration**

- Site URL: `http://localhost:5173`
- Redirect URLs: add `http://localhost:5173/**`

---

## 7. Verify setup

**Terminal 1 — backend:**

```powershell
cd e:\AgriSat\backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — verify script:**

```powershell
cd e:\AgriSat\backend
.\.venv\Scripts\python ..\scripts\verify_supabase.py
```

Expected: `Supabase connection: OK`, `PostGIS: OK`, `register_institution RPC: OK`

**Terminal 3 — frontend:**

```powershell
cd e:\AgriSat\frontend
npm run dev
```

---

## 8. Smoke test flow

1. Open http://localhost:5173/register
2. Create institution + admin account
3. Sign in → Dashboard
4. Register Field → draw polygon on map → submit
5. Confirm field appears on map with risk tier

---

## 9. RLS verification (institution isolation)

Run in SQL Editor after creating **two** test institutions:

```sql
-- As service role (backend), institution data is isolated by API layer.
-- Direct client access uses RLS:
SET request.jwt.claim.sub = 'USER_UUID_INST_A';
SET ROLE authenticated;
SELECT * FROM fields;  -- should only show institution A fields
```

Full automated RLS test: `scripts/verify_supabase.py --rls` (requires two test users).

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `Invalid token` on API calls | Check `SUPABASE_JWT_SECRET` matches dashboard JWT Secret |
| `PostGIS extension required` | Enable postgis in Database → Extensions |
| Field insert fails on boundary | Ensure migration `002_geometry_helpers.sql` is applied |
| `profile not found` after login | User registered via Supabase Auth but not via `/register-institution` |
| CORS errors | Add frontend URL to `CORS_ORIGINS` in backend `.env` |

---

## Security checklist

- [ ] `service_role` key only in `backend/.env` (never in frontend or git)
- [ ] `.env` files in `.gitignore`
- [ ] RLS enabled on all tenant tables (migration 001)
- [ ] Production: enable email confirmation + strong password policy
