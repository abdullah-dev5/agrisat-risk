"""Tier 2 — cloud-masked Sentinel-2 weekly composites via GEE (M4)."""

from datetime import date

from app.core.config import get_settings
from app.services.tiers.base import TierReading
from app.services.tiers.gee_client import fetch_tier2_composite_from_gee, is_gee_configured


def fetch_tier2_readings(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    if not get_settings().sen2sr_enabled or not is_gee_configured():
        return []
    return fetch_tier2_composite_from_gee(boundary_wkt, sowing_date, season_end)
