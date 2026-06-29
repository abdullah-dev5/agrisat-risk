"""Verify Google Earth Engine configuration (M3)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))


def main() -> int:
    print("=== AgriSat GEE verification ===\n")

    try:
        import ee  # noqa: F401
    except ImportError:
        print("FAIL: earthengine-api not installed. Run: pip install earthengine-api")
        return 1

    from app.services.tiers.gee_client import gee_health_probe, is_gee_configured

    if not is_gee_configured():
        print("SKIP: GEE not configured in backend/.env")
        print("See docs/GEE-SETUP.md")
        return 0

    result = gee_health_probe()
    print(f"configured:  {result['configured']}")
    print(f"connection:  {result['connection']}")
    print(f"message:     {result['message']}")

    if result["connection"] != "ok":
        print("\nFAIL: GEE connectivity check failed")
        return 1

    print("\nOK: GEE Tier 3 pipeline ready")
    print("Register or reprocess a field to pull live Sentinel readings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
