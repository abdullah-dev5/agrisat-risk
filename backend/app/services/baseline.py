"""Historical baseline construction (FR-4.x) — live GEE district baselines."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from statistics import mean, pstdev

from app.core.config import Settings
from app.models.enums import DataTier
from app.services.vegetation_index import effective_std, index_family_for_tier

logger = logging.getLogger(__name__)

BASELINE_MIN_ROWS = 5
BASELINE_MAX_AGE_DAYS = 30


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
    use_tier2_optical: bool = False,
) -> list[dict]:
    """Build multi-year baseline from historical GEE scenes over an AOI."""
    from app.services.tiers.gee_client import (
        GEEError,
        fetch_tier2_composite_from_gee,
        fetch_tier3_from_gee,
        is_gee_configured,
    )

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
            logger.warning("Baseline SAR year %s skipped: %s", year, exc)
            readings = []

        for r in readings:
            days = (r.acquisition_date - sow).days
            if days < 0:
                continue
            if r.sar_index is not None:
                sar_points.append({"days_since_sowing": days, "index_value": r.sar_index})
            if not use_tier2_optical and r.ndvi is not None:
                optical_points.append({"days_since_sowing": days, "index_value": r.ndvi})

        if use_tier2_optical:
            try:
                t2 = fetch_tier2_composite_from_gee(boundary_wkt, sow, season_end)
                for r in t2:
                    days = (r.acquisition_date - sow).days
                    if days >= 0 and r.ndvi is not None:
                        optical_points.append({"days_since_sowing": days, "index_value": r.ndvi})
            except GEEError as exc:
                logger.warning("Baseline Tier2 year %s skipped: %s", year, exc)

    rows: list[dict] = []
    if sar_points:
        rows.extend(build_baseline_from_readings(sar_points, DataTier.TIER3_SAR, sample_years))
    if optical_points:
        rows.extend(build_baseline_from_readings(optical_points, DataTier.TIER2_SEN2SR, sample_years))
    return rows


def _baseline_is_fresh(rows: list[dict]) -> bool:
    if len(rows) < BASELINE_MIN_ROWS:
        return False
    computed_values = [r.get("computed_at") for r in rows if r.get("computed_at")]
    if not computed_values:
        return False
    latest = max(computed_values)
    if isinstance(latest, str):
        latest_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
    else:
        latest_dt = latest
    age = datetime.now(timezone.utc) - latest_dt.astimezone(timezone.utc)
    return age.days < BASELINE_MAX_AGE_DAYS


def ensure_district_baseline(
    sb,
    settings: Settings,
    crop_type: str,
    pilot_district: str,
    reference_sowing: date,
    *,
    force: bool = False,
) -> list[dict]:
    """Load or build district-wide baseline from GEE over pilot bbox."""
    from app.services.district_geometry import pilot_district_wkt
    from app.services.tiers.gee_client import is_gee_configured

    existing = (
        sb.table("baseline_stats")
        .select("*")
        .eq("crop_type", crop_type)
        .eq("pilot_district", pilot_district)
        .execute()
        .data
        or []
    )

    if existing and _baseline_is_fresh(existing) and not force:
        return existing

    if not force and not settings.baseline_build_on_request:
        if existing:
            logger.info(
                "Using stale district baseline (%d rows); on-request build disabled",
                len(existing),
            )
        return existing

    if not is_gee_configured():
        return existing

    try:
        district_wkt = pilot_district_wkt(settings)
        rows = build_gee_baseline(
            district_wkt,
            reference_sowing,
            use_tier2_optical=settings.sen2sr_enabled,
        )
    except Exception as exc:
        logger.warning("District baseline build failed: %s", exc)
        return existing

    if not rows:
        return existing

    sb.table("baseline_stats").delete().eq("crop_type", crop_type).eq(
        "pilot_district", pilot_district
    ).execute()

    for b in rows:
        payload = {"crop_type": crop_type, "pilot_district": pilot_district, **b}
        try:
            sb.table("baseline_stats").insert(payload).execute()
        except Exception as exc:
            if "23505" in str(exc):
                continue
            raise

    return (
        sb.table("baseline_stats")
        .select("*")
        .eq("crop_type", crop_type)
        .eq("pilot_district", pilot_district)
        .execute()
        .data
        or rows
    )


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
