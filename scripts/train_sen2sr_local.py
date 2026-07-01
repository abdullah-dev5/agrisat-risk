"""Train local SEN2SR PyTorch weights (M4) on synthetic reflectance patches."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.core.config import BACKEND_ROOT, get_settings  # noqa: E402


def _synthetic_batch(batch_size: int, size: int = 32) -> tuple[np.ndarray, np.ndarray]:
    red = np.random.uniform(500, 2500, (batch_size, size, size)).astype(np.float32)
    nir = red + np.random.uniform(200, 3500, (batch_size, size, size)).astype(np.float32)
    blue = np.random.uniform(400, 2000, (batch_size, size, size)).astype(np.float32)
    green = (red + blue) / 2 + np.random.uniform(-200, 200, (batch_size, size, size)).astype(np.float32)
    x = np.stack([blue, green, red, nir], axis=1) / 10000.0

    ndvi = (nir - red) / np.maximum(nir + red, 1.0)
    y = np.zeros((batch_size, 1, size * 2, size * 2), dtype=np.float32)
    for i in range(batch_size):
        coarse = np.clip(ndvi[i], -1, 1)
        fine = np.kron(coarse, np.ones((2, 2))) / 4.0
        fine = np.clip((fine + 1) / 2, 0, 1)
        y[i, 0] = fine
    return x, y


def train(epochs: int = 8, batch_size: int = 16, out_dir: Path | None = None) -> Path:
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError as exc:
        raise SystemExit("PyTorch required: pip install torch") from exc

    from app.services.tiers.sen2sr_model import Sen2srNet

    settings = get_settings()
    out_dir = out_dir or (BACKEND_ROOT / settings.sen2sr_model_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "model.pt"

    x, y = _synthetic_batch(256)
    dataset = TensorDataset(torch.from_numpy(x), torch.from_numpy(y))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = Sen2srNet(scale=2)
    optim = torch.optim.Adam(model.parameters(), lr=1e-3)
    loss_fn = nn.MSELoss()

    model.train()
    for epoch in range(epochs):
        total = 0.0
        for xb, yb in loader:
            optim.zero_grad()
            pred = model(xb)
            loss = loss_fn(pred, yb)
            loss.backward()
            optim.step()
            total += float(loss.item())
        print(f"epoch {epoch + 1}/{epochs} loss={total / len(loader):.5f}")

    torch.save(model.state_dict(), out_path)
    print(f"[OK] SEN2SR model saved to {out_path}")
    return out_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train local SEN2SR model (synthetic bootstrap)")
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--out", type=str, default="")
    args = parser.parse_args()
    out = Path(args.out) if args.out else None
    train(epochs=args.epochs, out_dir=out)
