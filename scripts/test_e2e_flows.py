"""End-to-end flow test: Supabase Auth -> Backend API -> DB."""

from __future__ import annotations

import os
import sys
import time
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "frontend", ".env"))

import httpx

API = os.getenv("VITE_API_URL", "http://localhost:8000").rstrip("/")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "") or SERVICE_KEY

# Small polygon near Matiari District (~1 ha)
TEST_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [68.445, 25.595],
            [68.446, 25.595],
            [68.446, 25.596],
            [68.445, 25.596],
            [68.445, 25.595],
        ]
    ],
}


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def ok(msg: str) -> None:
    print(f"[OK] {msg}")


def supabase_sign_in(email: str, password: str) -> str:
    r = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Sign-in failed ({r.status_code}): {r.text[:300]}")
    return r.json()["access_token"]


def api_call(method: str, path: str, token: str | None = None, json_body: dict | None = None) -> httpx.Response:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{API}{path}", headers=headers, json=json_body, timeout=120)


def main() -> int:
    if not SUPABASE_URL or not SERVICE_KEY:
        return fail("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required in backend/.env")

    stamp = int(time.time())
    email = f"e2e-{stamp}-{uuid.uuid4().hex[:6]}@test.agrisat.local"
    password = "TestPass123!"

    print("=== AgriSat E2E flow test ===\n")

    # 1. Health
    r = httpx.get(f"{API}/health", timeout=10)
    if r.status_code != 200:
        return fail(f"Backend /health -> {r.status_code}")
    ok("Backend /health")

    r = httpx.get(f"{API}/health/supabase", timeout=15)
    body = r.json()
    if body.get("connection") != "ok":
        return fail(f"Backend /health/supabase connection: {body.get('connection')}")
    ok(f"Backend /health/supabase (tiers={body.get('tier_count')})")

    # 2. Register institution (frontend: api.registerInstitution)
    reg = {
        "name": f"E2E Test Bank {stamp}",
        "contact_email": f"contact-{stamp}@test.agrisat.local",
        "contact_phone": "+9203000000000",
        "admin_full_name": "E2E Admin",
        "admin_email": email,
        "admin_password": password,
    }
    r = api_call("POST", "/api/v1/auth/register-institution", json_body=reg)
    if r.status_code != 200:
        return fail(f"register-institution -> {r.status_code}: {r.text[:400]}")
    inst = r.json()
    if not inst.get("id"):
        return fail("register-institution missing institution id")
    ok(f"register-institution -> {inst['name']}")

    # 3. Sign in via Supabase (frontend: signInWithPassword)
    try:
        token = supabase_sign_in(email, password)
    except RuntimeError as exc:
        return fail(str(exc))
    ok("Supabase sign-in (JWT issued)")

    # 4. GET /auth/me
    r = api_call("GET", "/api/v1/auth/me", token=token)
    if r.status_code != 200:
        return fail(f"GET /auth/me -> {r.status_code}: {r.text[:300]}")
    me = r.json()
    if me.get("institution_id") != inst["id"]:
        return fail("profile institution_id mismatch")
    if me.get("role") != "admin":
        return fail(f"expected admin role, got {me.get('role')}")
    ok(f"GET /auth/me (institution={me['institution_id'][:8]}...)")

    # 5. POST /fields (frontend: api.createField)
    field_body = {
        "name": "E2E Test Field",
        "boundary_geojson": TEST_POLYGON,
        "crop_type": "wheat",
        "sowing_date": "2025-11-15",
        "farmer_ref_id": "FARM-E2E-001",
    }
    r = api_call("POST", "/api/v1/fields", token=token, json_body=field_body)
    if r.status_code != 200:
        return fail(f"POST /fields -> {r.status_code}: {r.text[:500]}")
    field = r.json()
    field_id = field.get("id")
    if not field_id:
        return fail("create field missing id")
    if field.get("boundary_geojson", {}).get("type") != "Polygon":
        return fail(f"boundary_geojson invalid: {field.get('boundary_geojson')}")
    if not field.get("current_risk_tier"):
        return fail("field missing current_risk_tier after processing")
    ok(f"POST /fields -> {field_id[:8]}... tier={field['current_risk_tier']}")

    # 6. GET /fields
    r = api_call("GET", "/api/v1/fields", token=token)
    if r.status_code != 200:
        return fail(f"GET /fields -> {r.status_code}")
    fields = r.json()
    if not any(f["id"] == field_id for f in fields):
        return fail("created field not in list")
    ok(f"GET /fields ({len(fields)} field(s))")

    # 7. GET /fields/{id}/detail
    r = api_call("GET", f"/api/v1/fields/{field_id}/detail", token=token)
    if r.status_code != 200:
        return fail(f"GET /fields/detail -> {r.status_code}: {r.text[:500]}")
    detail = r.json()
    if not detail.get("vegetation_readings"):
        return fail("field detail missing vegetation_readings")
    if not detail.get("current_assessment"):
        return fail("field detail missing current_assessment")
    ok(f"GET /fields/detail (readings={len(detail['vegetation_readings'])})")

    # 8. GET /reports/portfolio/summary
    r = api_call("GET", "/api/v1/reports/portfolio/summary", token=token)
    if r.status_code != 200:
        return fail(f"GET portfolio/summary -> {r.status_code}: {r.text[:300]}")
    summary = r.json()
    if summary.get("total_fields", 0) < 1:
        return fail("portfolio summary total_fields < 1")
    ok(f"GET portfolio/summary (total={summary['total_fields']})")

    # 9. GET PDF report
    r = api_call("GET", f"/api/v1/reports/field/{field_id}/pdf", token=token)
    if r.status_code != 200:
        return fail(f"GET field PDF -> {r.status_code}: {r.text[:200]}")
    if r.headers.get("content-type", "").startswith("application/pdf") and len(r.content) > 100:
        ok(f"GET field PDF ({len(r.content)} bytes)")
    else:
        return fail("PDF response invalid")

    # 10. GET CSV report
    r = api_call("GET", "/api/v1/reports/portfolio/csv", token=token)
    if r.status_code != 200:
        return fail(f"GET portfolio CSV -> {r.status_code}")
    if "field_id" in r.text or "E2E" in r.text:
        ok("GET portfolio/csv")
    else:
        return fail("CSV content unexpected")

    # 11. DB verification via service role
    from app.core.supabase_client import get_supabase_admin

    sb = get_supabase_admin()
    db_field = sb.table("fields").select("id, institution_id").eq("id", field_id).single().execute().data
    if db_field["institution_id"] != inst["id"]:
        return fail("DB field institution_id mismatch")
    readings = sb.table("vegetation_readings").select("id").eq("field_id", field_id).execute().data
    if not readings:
        return fail("DB vegetation_readings empty")
    assessment = (
        sb.table("risk_assessments")
        .select("risk_tier")
        .eq("field_id", field_id)
        .eq("is_current", True)
        .execute()
        .data
    )
    if not assessment:
        return fail("DB risk_assessments empty")
    ok("Supabase DB rows verified (fields, vegetation_readings, risk_assessments)")

    print("\nAll E2E flows passed.")
    print(f"Test user: {email} (password: {password})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
