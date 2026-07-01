"""Anomaly detection and risk scoring (FR-5.x)."""

from dataclasses import dataclass

from app.core.config import Settings
from app.models.enums import DataTier, RiskTier
from app.services.baseline import pick_baseline_row
from app.services.fusion import FusedReading
from app.services.vegetation_index import effective_std, index_family_for_tier


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
        DataTier.TIER3_SAR: "Sentinel-1 radar (used when clouds block optical imagery)",
    }
    return labels.get(tier, "satellite data") if tier else "satellite data"


def _index_label(tier: DataTier | None) -> str:
    if tier == DataTier.TIER3_SAR:
        return "radar backscatter index"
    return "vegetation greenness (NDVI)"


def _format_pct_diff(pct: float) -> str:
    capped = max(-99.0, min(99.0, pct))
    return f"{abs(capped):.0f}%"


def assess_risk(
    fused_readings: list[FusedReading],
    baseline: list[dict],
    sowing_date,
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
    if latest.index_value is None or latest.data_tier is None:
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
            explanation="Latest reading has no usable vegetation index.",
            audit_payload={"reason": "no_index", "latest": latest.__dict__},
        )

    b = pick_baseline_row(baseline, latest.days_since_sowing, latest.data_tier)
    if b is None:
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

    baseline_family = index_family_for_tier(str(b.get("primary_tier", "")))
    reading_family = index_family_for_tier(latest.data_tier.value)
    if baseline_family != reading_family:
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
            explanation=(
                f"Baseline is calibrated for {baseline_family} data but the latest reading uses "
                f"{reading_family} ({_index_label(latest.data_tier)}). "
                "Re-process the field after baseline refresh, or wait for clearer optical imagery."
            ),
            audit_payload={
                "reason": "baseline_family_mismatch",
                "baseline_family": baseline_family,
                "reading_family": reading_family,
            },
        )

    mean_idx = float(b["mean_index"])
    std_idx = effective_std(mean_idx, float(b["std_index"]))
    z = (latest.index_value - mean_idx) / std_idx

    if abs(z) > 8:
        return RiskResult(
            days_since_sowing=latest.days_since_sowing,
            z_score=round(z, 4),
            risk_tier=RiskTier.INSUFFICIENT_DATA,
            primary_data_tier=latest.data_tier,
            index_value=latest.index_value,
            baseline_mean=mean_idx,
            baseline_std=std_idx,
            rainfall_mm=rainfall_mm,
            rainfall_anomaly_pct=rainfall_anomaly_pct,
            explanation=(
                f"The {_index_label(latest.data_tier)} reading differs sharply from the historical baseline "
                f"(z-score {z:.1f}), which usually indicates a calibration or data-quality issue rather than "
                "a real crop anomaly. Manual review recommended — re-register or re-process after baseline update."
            ),
            audit_payload={
                "reason": "extreme_z_score",
                "z_score": z,
                "baseline": b,
                "latest_index": latest.index_value,
            },
        )

    risk_tier = _classify_zscore(z, settings)

    pct_diff = ((latest.index_value - mean_idx) / mean_idx) * 100 if mean_idx else 0
    direction = "below" if z < 0 else "above"
    tier_text = _tier_label(latest.data_tier)
    index_text = _index_label(latest.data_tier)

    rain_text = ""
    if rainfall_anomaly_pct is not None:
        if rainfall_anomaly_pct < -20:
            rain_text = " Rainfall in this period was below average, consistent with drought stress."
        elif rainfall_anomaly_pct > 20:
            rain_text = " Rainfall was above average, which may explain elevated vegetation signals."
    elif rainfall_mm is None:
        rain_text = " Rainfall data was unavailable for cross-check this period."

    explanation = (
        f"The {index_text} is {_format_pct_diff(pct_diff)} {direction} the {b.get('sample_years', 5)}-year "
        f"average for this crop stage (z-score: {z:.2f}), based on {tier_text}.{rain_text} "
        "This is decision-support information only — not an automated loan or claims decision."
    )

    if latest.data_tier == DataTier.TIER3_SAR:
        explanation += (
            " Radar measures surface roughness and moisture — interpret alongside optical NDVI when available."
        )

    if risk_tier in (RiskTier.WATCH, RiskTier.ELEVATED, RiskTier.HIGH) and rainfall_anomaly_pct is not None:
        if rainfall_anomaly_pct > -10 and z < 0:
            risk_tier = RiskTier.WATCH
            explanation += " Rainfall context suggests this anomaly may not be drought-related."

    base = RiskResult(
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

    from app.services.ml_risk import apply_ml_overlay

    return apply_ml_overlay(base, fused_readings, settings, rainfall_mm, rainfall_anomaly_pct)
