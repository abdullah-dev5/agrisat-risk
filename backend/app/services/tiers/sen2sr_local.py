"""Local SEN2SR inference — GEE patches + on-server PyTorch model (M4)."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from app.core.config import BACKEND_ROOT, Settings, get_settings
from app.services.tiers.base import TierReading
from app.services.tiers.gee_client import (
    GEEError,
    _ensure_gee_initialized,
    _end_date_exclusive,
    _wkt_to_ee_geometry,
    is_gee_configured,
)

logger = logging.getLogger(__name__)

REFLECTANCE_SCALE = 10000.0
MODEL_FILENAME = "model.pt"


def _resolve_model_path(settings: Settings | None = None) -> Path:
    settings = settings or get_settings()
    raw = Path(settings.sen2sr_model_path)
    if raw.is_absolute():
        return raw / MODEL_FILENAME
    return (BACKEND_ROOT / raw / MODEL_FILENAME).resolve()


def is_local_model_available(settings: Settings | None = None) -> bool:
    try:
        from app.services.tiers.sen2sr_model import TORCH_AVAILABLE
    except ImportError:
        return False
    if not TORCH_AVAILABLE:
        return False
    return _resolve_model_path(settings).is_file()


_model_cache: object | None = None
_model_cache_path: str | None = None


def _load_model(settings: Settings | None = None):
    global _model_cache, _model_cache_path
    from app.services.tiers.sen2sr_model import TORCH_AVAILABLE, Sen2srNet

    if not TORCH_AVAILABLE:
        raise RuntimeError("PyTorch not installed — pip install torch")
    settings = settings or get_settings()
    path = str(_resolve_model_path(settings))
    if _model_cache is not None and _model_cache_path == path:
        return _model_cache
    if not Path(path).is_file():
        raise FileNotFoundError(f"SEN2SR weights not found at {path}")
    import torch

    model = Sen2srNet(scale=2)
    state = torch.load(path, map_location="cpu", weights_only=True)
    model.load_state_dict(state)
    model.eval()
    _model_cache = model
    _model_cache_path = path
    return model


def _mask_s2(img):
    import ee

    scl = img.select("SCL")
    clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return img.updateMask(clear)


def _sample_reflectance(clear_img, region) -> np.ndarray:
    stacked = clear_img.select(["B2", "B3", "B4", "B8"])
    props = stacked.sampleRectangle(region=region, defaultValue=0).getInfo()["properties"]
    bands = [np.array(props[k], dtype=np.float32) for k in ("B2", "B3", "B4", "B8")]
    if any(a.size == 0 for a in bands):
        raise GEEError("Could not sample Sentinel-2 reflectance for local SEN2SR.")
    return np.stack(bands, axis=-1)


def _pad_to_min(patch: np.ndarray, min_size: int = 16) -> np.ndarray:
    h, w, c = patch.shape
    pad_h = max(0, min_size - h)
    pad_w = max(0, min_size - w)
    if pad_h == 0 and pad_w == 0:
        return patch
    return np.pad(patch, ((0, pad_h), (0, pad_w), (0, 0)), mode="edge")


def enhance_ndvi_from_patch(patch: np.ndarray, settings: Settings | None = None) -> float:
    """Run local model on a reflectance patch; return mean super-resolved NDVI."""
    import torch

    model = _load_model(settings)
    patch = _pad_to_min(patch)
    normed = np.clip(patch / REFLECTANCE_SCALE, 0.0, 1.0)
    tensor = torch.from_numpy(normed).permute(2, 0, 1).unsqueeze(0).float()
    with torch.no_grad():
        ndvi_hr = model(tensor).squeeze().numpy()
    valid = ndvi_hr[np.isfinite(ndvi_hr)]
    if valid.size == 0:
        raise GEEError("Local SEN2SR produced empty NDVI output.")
    return float(np.mean(valid))


def fetch_tier2_local_readings(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
    settings: Settings | None = None,
) -> list[TierReading]:
    """Tier 2 via GEE patches + local super-resolution model."""
    import ee

    settings = settings or get_settings()
    if not is_gee_configured():
        raise GEEError("GEE required to sample patches for local SEN2SR.")
    if not is_local_model_available(settings):
        raise FileNotFoundError("Local SEN2SR model weights not found.")

    _ensure_gee_initialized()
    end = season_end or date.today()
    region = _wkt_to_ee_geometry(boundary_wkt)
    readings: list[TierReading] = []
    week_start = sowing_date

    while week_start <= end:
        week_end = min(week_start + timedelta(days=6), end)
        end_exclusive = _end_date_exclusive(week_end)
        coll = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(week_start.isoformat(), end_exclusive)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 25))
            .map(_mask_s2)
        )
        if coll.size().getInfo() == 0:
            week_start += timedelta(days=7)
            continue

        composite = coll.median()
        patch = _sample_reflectance(composite, region)
        ndvi_val = enhance_ndvi_from_patch(patch, settings)
        # EVI from original-scale patch (model targets NDVI only)
        b2, b3, b4, b8 = patch[..., 0], patch[..., 1], patch[..., 2], patch[..., 3]
        nir, red, blue = b8.astype(np.float64), b4.astype(np.float64), b2.astype(np.float64)
        evi_denom = nir + 6 * red - 7.5 * blue + 1
        evi = np.where(evi_denom != 0, 2.5 * ((nir - red) / evi_denom), 0)
        evi_val = float(np.nanmean(evi[np.isfinite(evi)])) if np.isfinite(evi).any() else ndvi_val

        readings.append(
            TierReading(
                acquisition_date=week_end,
                ndvi=round(ndvi_val, 5),
                evi=round(evi_val, 5),
                cloud_fraction=0.0,
            )
        )
        week_start += timedelta(days=7)

    if not readings:
        raise GEEError("No clear Sentinel-2 scenes for local SEN2SR in this date range.")
    logger.info("Local SEN2SR: produced %d weekly readings", len(readings))
    return readings
