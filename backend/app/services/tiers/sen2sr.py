"""Tier 2 — SEN2SR super-resolution (M4 — not yet wired)."""

from datetime import date

from app.services.tiers.base import TierReading


def fetch_tier2_readings(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    # M4: wire tacofoundation/SEN2SR inference pipeline
    return []
