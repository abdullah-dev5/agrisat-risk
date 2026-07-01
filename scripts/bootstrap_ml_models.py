"""Bootstrap local SEN2SR + ML risk models for development (M4 + M12)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    print("=== Bootstrap ML models (M4 SEN2SR + M12 risk) ===\n")

    steps = [
        ([sys.executable, str(ROOT / "scripts" / "train_ml_risk_model.py")], "ML risk (sklearn)"),
        ([sys.executable, str(ROOT / "scripts" / "train_sen2sr_local.py"), "--epochs", "6"], "SEN2SR local (torch)"),
    ]

    failed = 0
    for cmd, label in steps:
        print(f"--- {label} ---")
        try:
            subprocess.run(cmd, cwd=ROOT, check=True)
        except subprocess.CalledProcessError:
            print(f"[SKIP] {label} failed — install deps: pip install scikit-learn joblib torch")
            failed += 1
        print()

    if failed == 2:
        return 1
    print("Done. Verify: GET /health/ml and GET /health/sen2sr")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
