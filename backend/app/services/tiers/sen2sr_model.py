"""Lightweight ESPCN-style super-resolution network for local SEN2SR (M4)."""

from __future__ import annotations

try:
    import torch
    import torch.nn as nn

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    TORCH_AVAILABLE = False
    nn = None  # type: ignore


if TORCH_AVAILABLE:

    class Sen2srNet(nn.Module):
        """2× super-resolution on 4-band reflectance patches (B2,B3,B4,B8)."""

        def __init__(self, scale: int = 2) -> None:
            super().__init__()
            self.scale = scale
            self.body = nn.Sequential(
                nn.Conv2d(4, 64, kernel_size=5, padding=2),
                nn.ReLU(inplace=True),
                nn.Conv2d(64, 32, kernel_size=3, padding=1),
                nn.ReLU(inplace=True),
                nn.Conv2d(32, 4 * (scale**2), kernel_size=3, padding=1),
                nn.PixelShuffle(scale),
                nn.Conv2d(4, 1, kernel_size=3, padding=1),
                nn.Sigmoid(),
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.body(x)

else:

    class Sen2srNet:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs) -> None:
            raise RuntimeError("PyTorch is required for Sen2srNet")
