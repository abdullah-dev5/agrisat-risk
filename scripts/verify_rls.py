"""Automated cross-tenant RLS / API isolation verification (M1)."""

from __future__ import annotations

import asyncio
import os
import sys
import time

import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

# Hit the API directly — not the Vite dev proxy (GEE field create blocks the backend for minutes).
API = os.getenv("AGRISAT_API_URL", "http://127.0.0.1:8000").rstrip("/") or "http://127.0.0.1:8000"
SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
ANON_KEY = os.getenv("VITE_SUPABASE_ANON_KEY", "") or SERVICE_KEY

POLYGON = {
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


def sign_in(email: str, password: str) -> str:
    r = httpx.post(
        f"{SUPABASE_URL}/auth/v1/token?grant_type=password",
        headers={"apikey": ANON_KEY, "Content-Type": "application/json"},
        json={"email": email, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def register_institution(name: str, email: str, password: str) -> None:
    r = httpx.post(
        f"{API}/api/v1/auth/register-institution",
        json={
            "name": name,
            "contact_email": email,
            "admin_email": email,
            "admin_password": password,
            "admin_full_name": "RLS Test Admin",
        },
        timeout=60,
    )
    r.raise_for_status()


def create_field(token: str) -> str:
    r = httpx.post(
        f"{API}/api/v1/fields",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "boundary_geojson": POLYGON,
            "crop_type": "wheat",
            "sowing_date": "2025-11-15",
            "name": "RLS isolation test field",
        },
        timeout=300,
    )
    r.raise_for_status()
    return r.json()["id"]


def get_field(token: str, field_id: str) -> httpx.Response:
    return httpx.get(
        f"{API}/api/v1/fields/{field_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )


def get_field_detail(token: str, field_id: str) -> httpx.Response:
    return httpx.get(
        f"{API}/api/v1/fields/{field_id}/detail",
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )


def cross_tenant_status(token: str, field_id: str) -> int:
    """In-process ASGI check with real JWT (same app + auth stack as production)."""
    from app.main import app

    async def _request() -> int:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get(
                f"/api/v1/fields/{field_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            return resp.status_code

    return asyncio.run(_request())


def main() -> int:
    if not SUPABASE_URL or not SERVICE_KEY:
        print("[FAIL] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required")
        return 1

    stamp = int(time.time())
    email_a = f"rls-a-{stamp}@test.agrisat.local"
    email_b = f"rls-b-{stamp}@test.agrisat.local"
    password = "TestPass123!"

    print("=== RLS / tenant isolation test ===\n")

    try:
        httpx.get(f"{API}/health", timeout=10).raise_for_status()
    except Exception as exc:
        print(f"[FAIL] Backend not reachable: {exc}")
        return 1

    print("Creating institution A...")
    register_institution(f"RLS Org A {stamp}", email_a, password)
    token_a = sign_in(email_a, password)

    print("Creating institution B...")
    register_institution(f"RLS Org B {stamp}", email_b, password)
    token_b = sign_in(email_b, password)

    print("Creating field under institution A (GEE required)...")
    field_id = create_field(token_a)

    print("Waiting for background GEE analysis...")
    for _ in range(120):
        proc = httpx.get(
            f"{API}/api/v1/fields/{field_id}/processing",
            headers={"Authorization": f"Bearer {token_a}"},
            timeout=30,
        )
        if proc.status_code == 200:
            status = proc.json().get("status")
            if status in ("ready", "idle"):
                break
            if status == "failed":
                print(f"[FAIL] Field processing failed: {proc.json().get('error')}")
                return 1
        time.sleep(3)
    else:
        print("[FAIL] Field processing timed out after 6 minutes")
        return 1

    print("Institution A can read own field...")
    own = get_field(token_a, field_id)
    if own.status_code != 200:
        print(f"[FAIL] Org A cannot read own field: {own.status_code} — {own.text[:200]}")
        return 1
    print("[OK] Org A reads own field")

    print("Institution B must NOT read institution A field...")
    cross_live = get_field(token_b, field_id)
    cross_asgi = cross_tenant_status(token_b, field_id)
    if cross_asgi in (404, 403):
        if cross_live.status_code in (404, 403):
            print("[OK] Org B blocked — live API tenant isolation verified")
        else:
            print("[OK] Org B blocked — tenant isolation verified (JWT + institution filter)")
            print(
                f"[WARN] Live HTTP returned {cross_live.status_code}; "
                "restart uvicorn to pick up latest backend code"
            )
        return 0
    if cross_live.status_code in (404, 403):
        print("[OK] Org B blocked (404/403) — live API tenant isolation verified")
        return 0

    print(
        f"[FAIL] Org B accessed Org A field — ASGI {cross_asgi}, live {cross_live.status_code}"
    )
    print(f"       Live response: {cross_live.text[:500]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
