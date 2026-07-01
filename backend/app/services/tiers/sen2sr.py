"""Tier 2 — local SEN2SR model (preferred) or GEE weekly composites (M4)."""

from datetime import date

from app.core.config import get_settings
from app.services.tiers.base import TierReading
from app.services.tiers.gee_client import fetch_tier2_composite_from_gee, is_gee_configured


def fetch_tier2_readings(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    settings = get_settings()
    if not settings.sen2sr_enabled:
        return []

    if settings.sen2sr_use_local:
        try:
            from app.services.tiers.sen2sr_local import (
                fetch_tier2_local_readings,
                is_local_model_available,
            )

            if is_local_model_available(settings):
                return fetch_tier2_local_readings(boundary_wkt, sowing_date, season_end, settings)
        except Exception:
            pass

    if is_gee_configured():
        return fetch_tier2_composite_from_gee(boundary_wkt, sowing_date, season_end)
    return []
