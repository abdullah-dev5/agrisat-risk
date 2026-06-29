"""Apply Supabase SQL migrations via direct Postgres connection."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "supabase" / "migrations"


def main() -> int:
    try:
        import psycopg2
    except ImportError:
        print("Install: pip install psycopg2-binary")
        return 1

    from dotenv import load_dotenv

    load_dotenv(ROOT / "backend" / ".env")
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        print("Set DATABASE_URL in backend/.env")
        return 1

    files = sorted(MIGRATIONS.glob("*.sql"))
    if not files:
        print(f"No migrations in {MIGRATIONS}")
        return 1

    print(f"Connecting to Supabase Postgres…")
    conn = psycopg2.connect(url)
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            for path in files:
                sql = path.read_text(encoding="utf-8")
                print(f"Applying {path.name}…")
                cur.execute(sql)
                print(f"  OK")
    except Exception as exc:
        print(f"FAILED: {exc}")
        return 1
    finally:
        conn.close()

    print("\nAll migrations applied.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
