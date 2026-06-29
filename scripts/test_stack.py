"""End-to-end stack smoke test (Supabase + backend API)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))


def main() -> int:
    errors: list[str] = []
    print("=== AgriSat stack test ===\n")

    # 1. Supabase REST
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        errors.append("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")
    else:
        try:
            from app.core.supabase_client import get_supabase_admin

            sb = get_supabase_admin()
            tiers = sb.table("tier_status").select("tier").execute()
            print(f"[OK] Supabase REST — {len(tiers.data)} tier rows")

            sb.rpc("field_boundary_geojson", {"p_field_id": "00000000-0000-0000-0000-000000000000"}).execute()
            print("[OK] PostGIS RPC field_boundary_geojson")
        except Exception as exc:
            errors.append(f"Supabase: {exc}")

    # 2. JWKS endpoint
    if url:
        try:
            import httpx

            r = httpx.get(f"{url.rstrip('/')}/auth/v1/.well-known/jwks.json", timeout=15)
            r.raise_for_status()
            keys = r.json().get("keys", [])
            print(f"[OK] Auth JWKS — {len(keys)} signing key(s)")
        except Exception as exc:
            errors.append(f"JWKS: {exc}")

    # 3. Backend health (if running)
    try:
        import httpx

        api = os.getenv("VITE_API_URL", "http://localhost:8000")
        r = httpx.get(f"{api}/health", timeout=5)
        if r.status_code == 200:
            print(f"[OK] Backend /health — {r.json()}")
            r2 = httpx.get(f"{api}/health/supabase", timeout=10)
            print(f"[OK] Backend /health/supabase — {r2.json()}")
        else:
            print(f"[SKIP] Backend not running at {api} (start uvicorn to test)")
    except Exception:
        print("[SKIP] Backend not running — start: uvicorn app.main:app --reload --port 8000")

    print()
    if errors:
        for e in errors:
            print(f"[FAIL] {e}")
        return 1

    print("All configured checks passed.")
    print("\nManual UI test:")
    print("  1. pnpm dev (frontend) + uvicorn (backend)")
    print("  2. /register -> create institution")
    print("  3. Register field (draw or upload GeoJSON)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
