"""Unit tests for the z-score risk engine.

ml_risk_enabled=False everywhere here so results are deterministic and don't
depend on backend/models/ml_risk/model.joblib -- that artifact is gitignored
(see docs/AUDIT-FINDINGS.md) and won't exist in a fresh CI checkout, so any
test coupled to it would pass locally and fail (or silently no-op) in CI.
"""
from datetime import date

from app.core.config import Settings
from app.models.enums import DataTier, RiskTier
from app.services.fusion import FusedReading
from app.services.risk_engine import assess_risk

SETTINGS = Settings(
    ml_risk_enabled=False,
    risk_threshold_watch=1.0,
    risk_threshold_elevated=1.5,
    risk_threshold_high=2.0,
)

SOWING = date(2025, 11, 15)


def _reading(day: int, ndvi: float, tier: DataTier = DataTier.TIER2_SEN2SR) -> FusedReading:
    return FusedReading(
        acquisition_date=date(2025, 12, 1),
        days_since_sowing=day,
        data_tier=tier,
        ndvi=ndvi if tier != DataTier.TIER3_SAR else None,
        sar_index=ndvi if tier == DataTier.TIER3_SAR else None,
        index_value=ndvi,
    )


def _baseline(day: int, mean: float, std: float, tier: str = "tier2_sen2sr") -> dict:
    return {
        "days_since_sowing": day,
        "mean_index": mean,
        "std_index": std,
        "sample_years": 5,
        "primary_tier": tier,
    }


def test_no_readings_is_insufficient_data():
    result = assess_risk([], [], SOWING, SETTINGS)
    assert result.risk_tier == RiskTier.INSUFFICIENT_DATA
    assert result.z_score is None
    assert result.audit_payload["reason"] == "no_readings"


def test_latest_reading_missing_index_is_insufficient_data():
    reading = FusedReading(
        acquisition_date=date(2025, 12, 1), days_since_sowing=30, data_tier=DataTier.TIER2_SEN2SR
    )
    result = assess_risk([reading], [_baseline(30, 0.6, 0.05)], SOWING, SETTINGS)
    assert result.risk_tier == RiskTier.INSUFFICIENT_DATA


def test_no_baseline_rows_at_all_is_insufficient_data():
    # pick_baseline_row only returns None when there are no baseline rows to
    # fall back to at all -- a mismatched-day row still gets picked (nearest
    # by day), so this specifically tests the empty-baseline case.
    result = assess_risk([_reading(30, 0.6)], [], SOWING, SETTINGS)
    assert result.risk_tier == RiskTier.INSUFFICIENT_DATA
    assert result.audit_payload["reason"] == "no_baseline"


def test_mismatched_index_family_is_insufficient_data():
    # latest reading is SAR but baseline was built from optical (sen2sr) data
    result = assess_risk(
        [_reading(30, 0.4, tier=DataTier.TIER3_SAR)],
        [_baseline(30, 0.6, 0.05, tier="tier2_sen2sr")],
        SOWING,
        SETTINGS,
    )
    assert result.risk_tier == RiskTier.INSUFFICIENT_DATA
    assert result.audit_payload["reason"] == "baseline_family_mismatch"


def test_extreme_z_score_is_treated_as_a_data_quality_issue():
    # index far outside any plausible range vs. a tight baseline -> |z| > 8
    result = assess_risk([_reading(30, 5.0)], [_baseline(30, 0.6, 0.05)], SOWING, SETTINGS)
    assert result.risk_tier == RiskTier.INSUFFICIENT_DATA
    assert result.audit_payload["reason"] == "extreme_z_score"


def test_reading_close_to_baseline_is_normal():
    result = assess_risk([_reading(30, 0.61)], [_baseline(30, 0.6, 0.05)], SOWING, SETTINGS)
    assert result.risk_tier == RiskTier.NORMAL


def test_reading_well_below_baseline_is_elevated_or_worse():
    # z = (0.4 - 0.6) / 0.05 = -4.0 -> comfortably past the "high" threshold (2.0)
    result = assess_risk([_reading(30, 0.4)], [_baseline(30, 0.6, 0.05)], SOWING, SETTINGS)
    assert result.risk_tier == RiskTier.HIGH
    assert result.z_score == -4.0


def test_low_rainfall_anomaly_does_not_downgrade_a_drought_flag():
    result = assess_risk(
        [_reading(30, 0.4)],
        [_baseline(30, 0.6, 0.05)],
        SOWING,
        SETTINGS,
        rainfall_mm=10.0,
        rainfall_anomaly_pct=-40.0,
    )
    assert result.risk_tier == RiskTier.HIGH
    assert "consistent with drought stress" in result.explanation


def test_normal_rainfall_downgrades_an_elevated_flag_to_watch():
    # z = (0.51 - 0.6) / 0.05 = -1.8 -> ELEVATED by threshold, but rainfall
    # doesn't support a drought story (anomaly > -10%), so the engine pulls
    # it back to WATCH rather than leaving an unsupported ELEVATED flag.
    result = assess_risk(
        [_reading(30, 0.51)],
        [_baseline(30, 0.6, 0.05)],
        SOWING,
        SETTINGS,
        rainfall_mm=120.0,
        rainfall_anomaly_pct=5.0,
    )
    assert result.risk_tier == RiskTier.WATCH
    assert "may not be drought-related" in result.explanation


def test_explanation_always_carries_the_decision_support_disclaimer():
    result = assess_risk([_reading(30, 0.6)], [_baseline(30, 0.6, 0.05)], SOWING, SETTINGS)
    assert "not an automated loan or claims decision" in result.explanation
