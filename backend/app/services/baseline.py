"""Historical baseline construction (FR-4.x) — live GEE only."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from statistics import mean, pstdev

from app.models.enums import DataTier
from app.services.vegetation_index import effective_std, index_family_for_tier

logger = logging.getLogger(__name__)


def build_baseline_from_readings(
    readings: list[dict],
    primary_tier: DataTier,
    sample_years: int = 5,
) -> list[dict]:
    by_day: dict[int, list[float]] = {}
    for r in readings:
        day = r["days_since_sowing"]
        val = r.get("index_value") or r.get("ndvi") or r.get("sar_index")
        if val is None:
            continue
        by_day.setdefault(day, []).append(float(val))

    baseline = []
    for day, values in sorted(by_day.items()):
        mu = mean(values)
        raw_std = pstdev(values) if len(values) > 1 else mu * 0.05
        baseline.append({
            "days_since_sowing": day,
            "mean_index": round(mu, 5),
            "std_index": round(effective_std(mu, raw_std), 5),
            "sample_years": sample_years,
            "primary_tier": primary_tier.value,
        })
    return baseline


def build_gee_baseline(
    boundary_wkt: str,
    reference_sowing: date,
    sample_years: int = 5,
) -> list[dict]:
    """Build multi-year baseline from historical Sentinel-1/2 scenes via GEE."""
    from app.services.tiers.gee_client import GEEError, fetch_tier3_from_gee, is_gee_configured

    if not is_gee_configured():
        return []

    sar_points: list[dict] = []
    optical_points: list[dict] = []
    season_length = max(30, min(180, (date.today() - reference_sowing).days))

    for offset in range(1, sample_years + 1):
        year = reference_sowing.year - offset
        try:
            sow = reference_sowing.replace(year=year)
        except ValueError:
            sow = reference_sowing.replace(year=year, day=28)
        season_end = sow + timedelta(days=season_length)

        try:
            readings = fetch_tier3_from_gee(boundary_wkt, sow, season_end)
        except GEEError as exc:
            logger.warning("Baseline year %s skipped: %s", year, exc)
            continue

        for r in readings:
            days = (r.acquisition_date - sow).days
            if days < 0:
                continue
            if r.ndvi is not None:
                optical_points.append({"days_since_sowing": days, "index_value": r.ndvi})
            if r.sar_index is not None:
                sar_points.append({"days_since_sowing": days, "index_value": r.sar_index})

    rows: list[dict] = []
    if sar_points:
        rows.extend(build_baseline_from_readings(sar_points, DataTier.TIER3_SAR, sample_years))
    if optical_points:
        rows.extend(build_baseline_from_readings(optical_points, DataTier.TIER2_SEN2SR, sample_years))
    return rows


def pick_baseline_row(
    baseline_rows: list[dict],
    days_since_sowing: int,
    data_tier: DataTier,
) -> dict | None:
    """Select the baseline row matching index family (SAR vs optical) and growth stage."""
    family = index_family_for_tier(data_tier.value)
    tier_rows = [
        b for b in baseline_rows
        if index_family_for_tier(str(b.get("primary_tier", "tier3_sar"))) == family
    ]
    if not tier_rows:
        tier_rows = baseline_rows

    if not tier_rows:
        return None

    return min(tier_rows, key=lambda b: abs(int(b["days_since_sowing"]) - days_since_sowing))
