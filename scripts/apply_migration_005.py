"""Apply migration 005 only (baseline per tier unique constraint)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "supabase" / "migrations" / "005_baseline_per_tier.sql"


def main() -> int:
    try:
        import psycopg2
    except ImportError:
        print("Install: pip install psycopg2-binary")
        return 1

    from dotenv import load_dotenv

    load_dotenv(ROOT / "backend" / ".env")
    url = os.getenv("DATABASE_URL", "").strip()
    if not url or "YOUR_PASSWORD" in url:
        print("[SKIP] Set a real DATABASE_URL in backend/.env (Supabase Dashboard -> Settings -> Database)")
        print("       Then run: python scripts/apply_migration_005.py")
        print("\nOr paste this SQL in Supabase SQL Editor:")
        print("-" * 60)
        print(SQL.read_text(encoding="utf-8"))
        print("-" * 60)
        return 2

    print("Applying 005_baseline_per_tier.sql…")
    conn = psycopg2.connect(url)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(SQL.read_text(encoding="utf-8"))
        print("OK — baseline_stats now allows separate SAR and optical rows per growth stage.")
        return 0
    except Exception as exc:
        if "already exists" in str(exc).lower():
            print("OK — constraint already applied.")
            return 0
        print(f"FAILED: {exc}")
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
