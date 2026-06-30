"""Build district-wide GEE baseline for pilot crop + district (M7)."""

from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from app.core.config import get_settings
from app.core.supabase_client import get_supabase_admin
from app.services.baseline import ensure_district_baseline


def main() -> int:
    settings = get_settings()
    sb = get_supabase_admin()
    reference_sowing = date(date.today().year, 11, 15)

    print(f"Building district baseline for {settings.pilot_crop} / {settings.pilot_district}...")
    rows = ensure_district_baseline(
        sb,
        settings,
        settings.pilot_crop,
        settings.pilot_district,
        reference_sowing,
        force=True,
    )
    print(f"Done — {len(rows)} baseline rows stored.")
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
