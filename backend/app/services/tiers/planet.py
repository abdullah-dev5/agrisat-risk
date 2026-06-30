"""Tier 1 — PlanetScope placeholder (requires E&R Program API key).

When Planet is not licensed, fusion falls back to Tier 2 (GEE weekly S2 composites)
then Tier 3 (Sentinel-1/2 + CHIRPS). No separate alternative pipeline is required.
"""

from datetime import date

from app.services.tiers.base import TierReading


def fetch_tier1_readings(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    # Planet Data API integration once E&R approval is granted (M5).
    return []
