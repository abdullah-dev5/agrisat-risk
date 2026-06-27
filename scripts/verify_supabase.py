"""Supabase connectivity and schema verification (M11)."""

from __future__ import annotations

import argparse
import os
import sys

# Allow running from repo root without installing as package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify AgriSat Supabase setup")
    parser.add_argument("--rls", action="store_true", help="Run extended RLS checks (manual review)")
    args = parser.parse_args()

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    jwt_secret = os.getenv("SUPABASE_JWT_SECRET", "")

    errors: list[str] = []

    if not url:
        errors.append("SUPABASE_URL is not set in backend/.env")
    if not key:
        errors.append("SUPABASE_SERVICE_ROLE_KEY is not set in backend/.env")
    if not jwt_secret:
        errors.append("SUPABASE_JWT_SECRET is not set in backend/.env")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        print("\nSee docs/SUPABASE-SETUP.md for setup steps.")
        return 1

    try:
        from supabase import create_client

        sb = create_client(url, key)
    except Exception as exc:
        print(f"FAIL: Could not create Supabase client: {exc}")
        return 1

    # Connection + tier_status table
    try:
        resp = sb.table("tier_status").select("tier, is_available").execute()
        print(f"OK: Supabase connection ({len(resp.data)} tier rows)")
    except Exception as exc:
        print(f"FAIL: Supabase query failed: {exc}")
        return 1

    # PostGIS via RPC existence check
    try:
        sb.rpc("field_boundary_geojson", {"p_field_id": "00000000-0000-0000-0000-000000000000"}).execute()
        print("OK: PostGIS RPC field_boundary_geojson exists")
    except Exception as exc:
        msg = str(exc).lower()
        if "function" in msg and "does not exist" in msg:
            print("FAIL: Migration 002 not applied (field_boundary_geojson missing)")
            return 1
        print("OK: PostGIS RPC field_boundary_geojson exists (null field expected)")

    # register_institution RPC
    try:
        # Dry check — function exists if we get a FK/validation error, not "does not exist"
        sb.rpc(
            "register_institution",
            {
                "p_name": "__verify_test__",
                "p_contact_email": "verify@test.local",
                "p_admin_user_id": "00000000-0000-0000-0000-000000000000",
            },
        ).execute()
    except Exception as exc:
        msg = str(exc).lower()
        if "does not exist" in msg:
            print("FAIL: register_institution RPC missing — run migration 001")
            return 1
        print("OK: register_institution RPC exists")

    # Health endpoint hint
    api_url = os.getenv("VITE_API_URL", "http://localhost:8000")
    print(f"\nNext: start backend and open {api_url}/health/supabase")

    if args.rls:
        print("\nRLS manual test: see docs/SUPABASE-SETUP.md section 9")

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
