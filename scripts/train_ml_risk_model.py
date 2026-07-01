"""Train M12 gradient-boosted crop stress classifier."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import BACKEND_ROOT, get_settings  # noqa: E402
from app.models.enums import RiskTier  # noqa: E402
from app.services.ml_risk import FEATURE_NAMES  # noqa: E402


def _tier_from_z(z: float) -> str:
    az = abs(z)
    if az >= 2.0:
        return RiskTier.HIGH.value
    if az >= 1.5:
        return RiskTier.ELEVATED.value
    if az >= 1.0:
        return RiskTier.WATCH.value
    return RiskTier.NORMAL.value


def _synthetic_dataset(n: int = 4000, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = random.Random(seed)
    rows: list[list[float]] = []
    labels: list[str] = []
    for _ in range(n):
        days = rng.randint(14, 130)
        baseline_mean = rng.uniform(0.28, 0.62)
        baseline_std = rng.uniform(0.025, 0.09)
        z = rng.gauss(0, 1.8)
        index_value = baseline_mean + z * baseline_std
        rainfall_mm = max(0.0, rng.gauss(35, 18))
        rainfall_anomaly = rng.gauss(0, 22)
        is_sar = float(rng.random() < 0.25)
        ndvi_trend = rng.gauss(-0.02 if z < 0 else 0.01, 0.03)
        reading_count = rng.randint(3, 24)
        rows.append(
            [
                float(days),
                float(index_value),
                baseline_mean,
                baseline_std,
                z,
                rainfall_mm,
                rainfall_anomaly,
                is_sar,
                ndvi_trend,
                float(reading_count),
            ]
        )
        labels.append(_tier_from_z(z))
    return np.array(rows, dtype=np.float64), np.array(labels)


def train_from_supabase(out_dir: Path | None = None) -> Path:
    """Optional: train from historical risk_assessments when enough rows exist."""
    from app.core.supabase_client import get_supabase_admin

    settings = get_settings()
    out_dir = out_dir or (BACKEND_ROOT / settings.ml_risk_model_path)
    sb = get_supabase_admin()
    rows = (
        sb.table("risk_assessments")
        .select("days_since_sowing,index_value,baseline_mean,baseline_std,z_score,rainfall_mm,rainfall_anomaly_pct,risk_tier,primary_data_tier")
        .eq("is_current", True)
        .limit(5000)
        .execute()
        .data
    )
    if len(rows) < 50:
        raise RuntimeError(f"Need ≥50 assessments for DB training; found {len(rows)}. Use synthetic bootstrap.")

    x_rows: list[list[float]] = []
    y_rows: list[str] = []
    for r in rows:
        if r.get("z_score") is None or r.get("risk_tier") in (None, RiskTier.INSUFFICIENT_DATA.value):
            continue
        x_rows.append(
            [
                float(r["days_since_sowing"]),
                float(r.get("index_value") or 0),
                float(r.get("baseline_mean") or 0.4),
                float(r.get("baseline_std") or 0.05),
                float(r["z_score"]),
                float(r.get("rainfall_mm") or 0),
                float(r.get("rainfall_anomaly_pct") or 0),
                1.0 if r.get("primary_data_tier") == "tier3_sar" else 0.0,
                0.0,
                10.0,
            ]
        )
        y_rows.append(r["risk_tier"])
    return _fit_and_save(np.array(x_rows), np.array(y_rows), out_dir)


def _fit_and_save(x: np.ndarray, y: np.ndarray, out_dir: Path) -> Path:
    import joblib
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.model_selection import train_test_split

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "model.joblib"

    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, random_state=42, stratify=y)
    model = GradientBoostingClassifier(
        n_estimators=120,
        max_depth=4,
        learning_rate=0.08,
        random_state=42,
    )
    model.fit(x_train, y_train)
    score = model.score(x_test, y_test)
    classes = sorted(set(y.tolist()), key=lambda c: ["normal", "watch", "elevated", "high", "insufficient_data"].index(c) if c in ("normal", "watch", "elevated", "high", "insufficient_data") else 99)
    artifact = {
        "model": model,
        "classes": classes,
        "feature_names": FEATURE_NAMES,
        "version": "1",
        "test_accuracy": round(float(score), 4),
    }
    joblib.dump(artifact, out_path)
    print(f"[OK] ML risk model saved to {out_path} (holdout accuracy {score:.3f})")
    return out_path


def train_synthetic(out_dir: Path | None = None) -> Path:
    settings = get_settings()
    out_dir = out_dir or (BACKEND_ROOT / settings.ml_risk_model_path)
    x, y = _synthetic_dataset()
    return _fit_and_save(x, y, out_dir)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train M12 gradient-boosted risk model")
    parser.add_argument("--from-db", action="store_true", help="Train from Supabase risk_assessments")
    parser.add_argument("--out", type=str, default="")
    args = parser.parse_args()
    out = Path(args.out) if args.out else None
    if args.from_db:
        train_from_supabase(out)
    else:
        train_synthetic(out)
