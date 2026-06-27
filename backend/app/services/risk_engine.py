"""Anomaly detection and risk scoring (FR-5.x)."""

from dataclasses import dataclass
from datetime import date, timedelta

from app.core.config import Settings
from app.models.enums import DataTier, RiskTier
from app.services.fusion import FusedReading


@dataclass
class RiskResult:
    days_since_sowing: int
    z_score: float | None
    risk_tier: RiskTier
    primary_data_tier: DataTier | None
    index_value: float | None
    baseline_mean: float | None
    baseline_std: float | None
    rainfall_mm: float | None
    rainfall_anomaly_pct: float | None
    explanation: str
    audit_payload: dict


def _classify_zscore(z: float, settings: Settings) -> RiskTier:
    abs_z = abs(z)
    if abs_z >= settings.risk_threshold_high:
        return RiskTier.HIGH
    if abs_z >= settings.risk_threshold_elevated:
        return RiskTier.ELEVATED
    if abs_z >= settings.risk_threshold_watch:
        return RiskTier.WATCH
    return RiskTier.NORMAL


def _tier_label(tier: DataTier | None) -> str:
    labels = {
        DataTier.TIER1_PLANET: "high-resolution PlanetScope imagery",
        DataTier.TIER2_SEN2SR: "SEN2SR-enhanced Sentinel-2 imagery (AI super-resolution)",
        DataTier.TIER3_SAR: "radar (Sentinel-1) data due to cloud cover or optical unavailability",
    }
    return labels.get(tier, "satellite data") if tier else "satellite data"


def assess_risk(
    fused_readings: list[FusedReading],
    baseline: list[dict],
    sowing_date: date,
    settings: Settings,
    rainfall_mm: float | None = None,
    rainfall_anomaly_pct: float | None = None,
) -> RiskResult:
    if not fused_readings:
        return RiskResult(
            days_since_sowing=0,
            z_score=None,
            risk_tier=RiskTier.INSUFFICIENT_DATA,
            primary_data_tier=None,
            index_value=None,
            baseline_mean=None,
            baseline_std=None,
            rainfall_mm=rainfall_mm,
            rainfall_anomaly_pct=rainfall_anomaly_pct,
            explanation=(
                "Insufficient satellite data for this field in the current period. "
                "No risk status can be determined — manual review recommended."
            ),
            audit_payload={"reason": "no_readings"},
        )

    latest = fused_readings[-1]
    baseline_map = {b["days_since_sowing"]: b for b in baseline}

    nearest_day = min(baseline_map.keys(), key=lambda d: abs(d - latest.days_since_sowing), default=None)
    if nearest_day is None or latest.index_value is None:
        return RiskResult(
            days_since_sowing=latest.days_since_sowing,
            z_score=None,
            risk_tier=RiskTier.INSUFFICIENT_DATA,
            primary_data_tier=latest.data_tier,
            index_value=latest.index_value,
            baseline_mean=None,
            baseline_std=None,
            rainfall_mm=rainfall_mm,
            rainfall_anomaly_pct=rainfall_anomaly_pct,
            explanation="Historical baseline unavailable for comparison at this crop growth stage.",
            audit_payload={"reason": "no_baseline", "latest": latest.__dict__},
        )

    b = baseline_map[nearest_day]
    mean_idx = float(b["mean_index"])
    std_idx = float(b["std_index"])
    z = (latest.index_value - mean_idx) / std_idx

    risk_tier = _classify_zscore(z, settings)

    pct_diff = ((latest.index_value - mean_idx) / mean_idx) * 100 if mean_idx else 0
    direction = "below" if z < 0 else "above"
    tier_text = _tier_label(latest.data_tier)

    rain_text = ""
    if rainfall_anomaly_pct is not None:
        if rainfall_anomaly_pct < -20:
            rain_text = " Rainfall in this period was below average, consistent with drought stress."
        elif rainfall_anomaly_pct > 20:
            rain_text = " Rainfall was above average, which may explain elevated vegetation signals."

    explanation = (
        f"Vegetation health is {abs(pct_diff):.0f}% {direction} the {b.get('sample_years', 5)}-year average "
        f"for this crop stage (z-score: {z:.2f}), based on {tier_text}.{rain_text} "
        "This is decision-support information only — not an automated loan or claims decision."
    )

    if risk_tier in (RiskTier.WATCH, RiskTier.ELEVATED, RiskTier.HIGH) and rainfall_anomaly_pct is not None:
        if rainfall_anomaly_pct > -10 and z < 0:
            risk_tier = RiskTier.WATCH
            explanation += " Rainfall context suggests this anomaly may not be drought-related."

    return RiskResult(
        days_since_sowing=latest.days_since_sowing,
        z_score=round(z, 4),
        risk_tier=risk_tier,
        primary_data_tier=latest.data_tier,
        index_value=latest.index_value,
        baseline_mean=mean_idx,
        baseline_std=std_idx,
        rainfall_mm=rainfall_mm,
        rainfall_anomaly_pct=rainfall_anomaly_pct,
        explanation=explanation,
        audit_payload={
            "latest_reading": {
                "date": latest.acquisition_date.isoformat(),
                "tier": latest.data_tier.value,
                "index": latest.index_value,
            },
            "baseline": b,
            "z_score": z,
            "rainfall_mm": rainfall_mm,
            "rainfall_anomaly_pct": rainfall_anomaly_pct,
        },
    )
