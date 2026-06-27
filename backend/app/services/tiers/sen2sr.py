"""Tier 2 — SEN2SR super-resolution placeholder."""

from datetime import date

from app.services.tiers.base import TierReading
from app.services.tiers.demo_data import generate_demo_readings


def fetch_tier2_readings(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    # TODO: wire tacofoundation/SEN2SR inference pipeline
    return generate_demo_readings(sowing_date, tier="tier2_sen2sr")
