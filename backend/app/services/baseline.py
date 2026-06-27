"""Historical baseline construction (FR-4.x)."""

from statistics import mean, pstdev

from app.core.config import Settings
from app.models.enums import DataTier
from app.services.tiers.demo_data import generate_demo_readings


def build_baseline_from_readings(
    readings: list[dict],
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
        baseline.append({
            "days_since_sowing": day,
            "mean_index": round(mean(values), 5),
            "std_index": round(max(pstdev(values), 0.01), 5),
            "sample_years": sample_years,
            "primary_tier": DataTier.TIER3_SAR.value,
        })
    return baseline


def generate_demo_baseline(settings: Settings) -> list[dict]:
    from datetime import date, timedelta

    readings: list[dict] = []
    for year_offset in range(1, 6):
        sow = date(date.today().year - year_offset, 11, 15)
        for r in generate_demo_readings(sow, "tier3_sar"):
            idx = r.sar_index or r.ndvi
            if idx is None:
                continue
            readings.append({
                "days_since_sowing": (r.acquisition_date - sow).days,
                "index_value": idx,
            })
    return build_baseline_from_readings(readings)
