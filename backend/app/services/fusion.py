"""Deterministic tier-selection and fusion (FR-3.4)."""

from dataclasses import dataclass
from datetime import date

from app.models.enums import DataTier
from app.services.tiers.base import (
    Tier1Adapter,
    Tier2Adapter,
    Tier3Adapter,
    TierFetchResult,
    TierReading,
)


@dataclass
class FusedReading:
    acquisition_date: date
    days_since_sowing: int
    data_tier: DataTier
    ndvi: float | None = None
    evi: float | None = None
    sar_index: float | None = None
    cloud_fraction: float | None = None
    index_value: float | None = None


@dataclass
class FusionResult:
    readings: list[FusedReading]
    pipeline: dict[str, str]


def _primary_index(reading: TierReading) -> float | None:
    if reading.ndvi is not None:
        return reading.ndvi
    if reading.sar_index is not None:
        return reading.sar_index
    return None


def select_and_fuse(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> FusionResult:
    tier1 = Tier1Adapter()
    tier2 = Tier2Adapter()
    tier3 = Tier3Adapter()

    t1_readings = tier1.fetch_readings(boundary_wkt, sowing_date, season_end)
    t1_result = TierFetchResult(
        readings=t1_readings,
        source="planet" if tier1.is_available() and t1_readings else "empty",
    )
    t2_result = tier2.fetch_with_meta(boundary_wkt, sowing_date, season_end)
    t3_result = tier3.fetch_with_meta(boundary_wkt, sowing_date, season_end)

    t1_by_date = {r.acquisition_date: r for r in t1_result.readings}
    t2_by_date = {r.acquisition_date: r for r in t2_result.readings}
    t3_by_date = {r.acquisition_date: r for r in t3_result.readings}

    all_dates = sorted(set(t1_by_date) | set(t2_by_date) | set(t3_by_date))
    fused: list[FusedReading] = []

    for acq in all_dates:
        days = (acq - sowing_date).days
        if days < 0:
            continue

        chosen_tier: DataTier
        reading: TierReading | None = None

        if acq in t1_by_date and tier1.is_available():
            chosen_tier = DataTier.TIER1_PLANET
            reading = t1_by_date[acq]
        elif acq in t2_by_date:
            t2 = t2_by_date[acq]
            if t2.cloud_fraction is None or t2.cloud_fraction < 0.5:
                chosen_tier = DataTier.TIER2_SEN2SR
                reading = t2
            elif acq in t3_by_date:
                chosen_tier = DataTier.TIER3_SAR
                reading = t3_by_date[acq]
            else:
                continue
        elif acq in t3_by_date:
            chosen_tier = DataTier.TIER3_SAR
            reading = t3_by_date[acq]
        else:
            continue

        index_value = _primary_index(reading)
        fused.append(
            FusedReading(
                acquisition_date=acq,
                days_since_sowing=days,
                data_tier=chosen_tier,
                ndvi=reading.ndvi,
                evi=reading.evi,
                sar_index=reading.sar_index,
                cloud_fraction=reading.cloud_fraction,
                index_value=index_value,
            )
        )

    pipeline = {
        "tier1": t1_result.source,
        "tier2": t2_result.source,
        "tier3": t3_result.source,
        "vegetation_source": t3_result.source,
        "reading_count": str(len(fused)),
    }

    return FusionResult(readings=fused, pipeline=pipeline)
