"""Reprocess all active fields with live GEE (refresh baselines + risk scores)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_admin
from app.services.field_service import process_field
from app.services.tiers.gee_client import is_gee_configured


def main() -> int:
    if not is_gee_configured():
        print("[FAIL] GEE not configured — set credentials in backend/.env")
        return 1

    sb = get_supabase_admin()
    resp = sb.table("fields").select("id, name, farmer_ref_id").eq("status", "active").execute()
    fields = resp.data or []

    if not fields:
        print("No active fields to reprocess.")
        return 0

    settings = get_settings()
    print(f"Reprocessing {len(fields)} field(s) with live GEE...\n")

    failed = 0
    for row in fields:
        label = row.get("name") or row.get("farmer_ref_id") or row["id"][:8]
        print(f"  -> {label} ({row['id']})...", flush=True)
        try:
            process_field(row["id"], settings)
            print("    OK")
        except Exception as exc:
            failed += 1
            print(f"    FAILED: {exc}")

    print(f"\nDone. {len(fields) - failed}/{len(fields)} succeeded.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
