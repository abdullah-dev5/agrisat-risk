"""Tier 1 — PlanetScope placeholder (requires E&R Program API key)."""

from datetime import date

from app.services.tiers.base import TierReading


def fetch_tier1_readings(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    # TODO: Planet Data API integration once E&R approval is granted
    return []
