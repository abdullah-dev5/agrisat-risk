"""M12 — gradient-boosted crop stress model (FR-5.5)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import BACKEND_ROOT, Settings, get_settings
from app.models.enums import DataTier, RiskTier
from app.services.fusion import FusedReading
from app.services.risk_engine import RiskResult

logger = logging.getLogger(__name__)

MODEL_FILENAME = "model.joblib"
FEATURE_NAMES = [
    "days_since_sowing",
    "index_value",
    "baseline_mean",
    "baseline_std",
    "z_score",
    "rainfall_mm",
    "rainfall_anomaly_pct",
    "is_sar",
    "ndvi_trend",
    "reading_count",
]

TIER_ORDER = [RiskTier.NORMAL, RiskTier.WATCH, RiskTier.ELEVATED, RiskTier.HIGH]


def _resolve_model_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    raw = Path(settings.ml_risk_model_path)
    if raw.is_absolute():
        return raw / MODEL_FILENAME
    return (BACKEND_ROOT / raw / MODEL_FILENAME).resolve()


def is_ml_model_available(settings: Settings | None = None) -> bool:
    return _resolve_model_path(settings).is_file()


def _load_artifact(settings: Settings | None = None) -> dict[str, Any]:
    import joblib

    settings = settings or get_settings()
    path = _resolve_model_path(settings)
    if not path.is_file():
        raise FileNotFoundError(f"ML risk model not found at {path}")
    return joblib.load(path)


_artifact_cache: dict[str, Any] | None = None
_artifact_cache_path: str | None = None


def _get_artifact(settings: Settings | None = None) -> dict[str, Any]:
    global _artifact_cache, _artifact_cache_path
    settings = settings or get_settings()
    path = str(_resolve_model_path(settings))
    if _artifact_cache is not None and _artifact_cache_path == path:
        return _artifact_cache
    _artifact_cache = _load_artifact(settings)
    _artifact_cache_path = path
    return _artifact_cache


def _ndvi_trend(readings: list[FusedReading]) -> float:
    if len(readings) < 2:
        return 0.0
    tail = readings[-3:]
    values = [r.index_value for r in tail if r.index_value is not None]
    if len(values) < 2:
        return 0.0
    return float(values[-1] - values[0]) / max(len(values) - 1, 1)


def build_feature_vector(
    fused_readings: list[FusedReading],
    result: RiskResult,
    rainfall_mm: float | None,
    rainfall_anomaly_pct: float | None,
) -> np.ndarray:
    latest = fused_readings[-1] if fused_readings else None
    is_sar = 1.0 if latest and latest.data_tier == DataTier.TIER3_SAR else 0.0
    return np.array(
        [
            float(result.days_since_sowing),
            float(result.index_value or 0.0),
            float(result.baseline_mean or 0.0),
            float(result.baseline_std or 0.05),
            float(result.z_score or 0.0),
            float(rainfall_mm or 0.0),
            float(rainfall_anomaly_pct or 0.0),
            is_sar,
            _ndvi_trend(fused_readings),
            float(len(fused_readings)),
        ],
        dtype=np.float64,
    )


def predict_ml_risk(
    fused_readings: list[FusedReading],
    result: RiskResult,
    rainfall_mm: float | None = None,
    rainfall_anomaly_pct: float | None = None,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()
    artifact = _get_artifact(settings)
    model = artifact["model"]
    features = build_feature_vector(fused_readings, result, rainfall_mm, rainfall_anomaly_pct)
    proba = model.predict_proba(features.reshape(1, -1))[0]
    classes: list[str] = artifact.get("classes", [t.value for t in TIER_ORDER])
    stress_idx = max(range(len(classes)), key=lambda i: proba[i] if classes[i] != RiskTier.NORMAL.value else -1)
    predicted_tier = classes[stress_idx]
    stress_probability = float(1.0 - proba[classes.index(RiskTier.NORMAL.value)]) if RiskTier.NORMAL.value in classes else float(max(proba))
    return {
        "model_version": artifact.get("version", "1"),
        "predicted_tier": predicted_tier,
        "stress_probability": round(stress_probability, 4),
        "class_probabilities": {c: round(float(p), 4) for c, p in zip(classes, proba)},
        "features": dict(zip(FEATURE_NAMES, features.tolist())),
    }


def _tier_rank(tier: RiskTier) -> int:
    try:
        return TIER_ORDER.index(tier)
    except ValueError:
        return 0


def apply_ml_overlay(
    result: RiskResult,
    fused_readings: list[FusedReading],
    settings: Settings,
    rainfall_mm: float | None = None,
    rainfall_anomaly_pct: float | None = None,
) -> RiskResult:
    if not settings.ml_risk_enabled or not is_ml_model_available(settings):
        return result
    if result.risk_tier == RiskTier.INSUFFICIENT_DATA:
        return result

    try:
        ml = predict_ml_risk(fused_readings, result, rainfall_mm, rainfall_anomaly_pct, settings)
    except Exception as exc:
        logger.warning("ML risk overlay skipped: %s", exc)
        return result

    ml_tier = RiskTier(ml["predicted_tier"])
    z_tier = result.risk_tier
    final_tier = z_tier

    if settings.ml_risk_elevate_only:
        if _tier_rank(ml_tier) > _tier_rank(z_tier) and ml["stress_probability"] >= settings.ml_risk_confidence_min:
            final_tier = ml_tier
    elif ml["stress_probability"] >= settings.ml_risk_confidence_min:
        final_tier = ml_tier

    ml_note = (
        f" ML stress model (gradient boosting v{ml['model_version']}) estimates "
        f"{ml['stress_probability']:.0%} crop-stress probability (predicted tier: {ml['predicted_tier'].replace('_', ' ')})."
    )
    explanation = result.explanation + ml_note
    if final_tier != z_tier:
        explanation += f" Tier elevated from {z_tier.value} to {final_tier.value} based on ML agreement."

    audit = {
        **result.audit_payload,
        "ml": ml,
        "ml_applied_tier": final_tier.value,
        "z_score_tier": z_tier.value,
    }
    return RiskResult(
        days_since_sowing=result.days_since_sowing,
        z_score=result.z_score,
        risk_tier=final_tier,
        primary_data_tier=result.primary_data_tier,
        index_value=result.index_value,
        baseline_mean=result.baseline_mean,
        baseline_std=result.baseline_std,
        rainfall_mm=result.rainfall_mm,
        rainfall_anomaly_pct=result.rainfall_anomaly_pct,
        explanation=explanation,
        audit_payload=audit,
    )
