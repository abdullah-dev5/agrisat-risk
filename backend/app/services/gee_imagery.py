"""GEE field imagery — latest RGB + NDVI previews for growth monitoring."""

from __future__ import annotations

import base64
import io
import logging
from datetime import date, timedelta
from typing import Any

import numpy as np
from PIL import Image

from app.services.tiers.gee_client import GEEError, _ensure_gee_initialized, _wkt_to_ee_geometry, is_gee_configured

logger = logging.getLogger(__name__)

RGB_MIN = 0
RGB_MAX = 3000
NDVI_MIN = 0.0
NDVI_MAX = 0.85
NDVI_PALETTE = ("#a50026", "#fee08b", "#006837")


def _mask_s2(img):
    import ee

    scl = img.select("SCL")
    clear = scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    return img.updateMask(clear)


def _latest_clear_scene(region, start: date, end: date, before: date | None = None):
    import ee

    end_exclusive = (end + timedelta(days=1)).isoformat()
    coll = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start.isoformat(), end_exclusive)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 25))
        .sort("system:time_start", False)
    )
    if before:
        coll = coll.filter(ee.Filter.lt("system:time_start", ee.Date(before.isoformat()).millis()))
    if coll.size().getInfo() == 0:
        return None
    img = ee.Image(coll.first())
    props = img.toDictionary(["system:time_start", "CLOUDY_PIXEL_PERCENTAGE"]).getInfo()
    ts = props.get("system:time_start")
    acq = date.fromtimestamp(ts / 1000) if ts else end
    cloud = float(props.get("CLOUDY_PIXEL_PERCENTAGE") or 0)
    return img, acq, cloud


def _hex_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)


def _to_data_url(rgb_array: np.ndarray) -> str:
    img = Image.fromarray(rgb_array.astype(np.uint8), mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _sample_arrays(clear_img, region) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    stacked = clear_img.select(["B4", "B3", "B2"]).addBands(
        clear_img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    )
    props = stacked.sampleRectangle(region=region, defaultValue=0).getInfo()["properties"]
    arrays = (
        np.array(props["B4"], dtype=np.float32),
        np.array(props["B3"], dtype=np.float32),
        np.array(props["B2"], dtype=np.float32),
        np.array(props["NDVI"], dtype=np.float32),
    )
    if any(a.size == 0 for a in arrays):
        raise GEEError("Could not sample Sentinel-2 pixels for this field boundary.")
    return arrays


def _rgb_preview(r: np.ndarray, g: np.ndarray, b: np.ndarray) -> str:
    def scale(arr: np.ndarray) -> np.ndarray:
        return np.clip((arr - RGB_MIN) / (RGB_MAX - RGB_MIN) * 255, 0, 255)

    rgb = np.stack([scale(r), scale(g), scale(b)], axis=-1)
    return _to_data_url(rgb)


def _ndvi_preview(ndvi: np.ndarray) -> str:
    norm = np.clip((ndvi - NDVI_MIN) / (NDVI_MAX - NDVI_MIN), 0, 1)
    low = np.array(_hex_rgb(NDVI_PALETTE[0]), dtype=np.float32)
    mid = np.array(_hex_rgb(NDVI_PALETTE[1]), dtype=np.float32)
    high = np.array(_hex_rgb(NDVI_PALETTE[2]), dtype=np.float32)

    t_lower = np.clip(norm / 0.5, 0, 1)[..., None]
    rgb_lower = low + (mid - low) * t_lower

    t_upper = np.clip((norm - 0.5) / 0.5, 0, 1)[..., None]
    rgb_upper = mid + (high - mid) * t_upper

    rgb = np.where((norm[..., None] <= 0.5), rgb_lower, rgb_upper)
    return _to_data_url(rgb.astype(np.uint8))


def _scene_stats(ndvi: np.ndarray) -> dict[str, float | None]:
    valid = ndvi[np.isfinite(ndvi) & (ndvi > -1) & (ndvi < 1)]
    if valid.size == 0:
        return {"ndvi_mean": None}
    return {"ndvi_mean": round(float(valid.mean()), 4)}


def _pack_scene(clear_img, region, acq: date, cloud_pct: float) -> dict[str, Any]:
    r, g, b, ndvi = _sample_arrays(clear_img, region)
    stats = _scene_stats(ndvi)
    return {
        "date": acq.isoformat(),
        "cloud_pct": round(cloud_pct, 1),
        "ndvi_mean": stats["ndvi_mean"],
        "rgb": {"thumb_url": _rgb_preview(r, g, b), "tiles": None},
        "ndvi": {"thumb_url": _ndvi_preview(ndvi), "tiles": None},
    }


def fetch_field_imagery(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> dict[str, Any]:
    """Return latest + comparison Sentinel-2 RGB/NDVI previews from GEE pixel samples."""
    if not is_gee_configured():
        raise GEEError("GEE not configured")

    _ensure_gee_initialized()
    end = season_end or date.today()
    region = _wkt_to_ee_geometry(boundary_wkt)

    latest = _latest_clear_scene(region, sowing_date, end)
    if not latest:
        raise GEEError("No clear Sentinel-2 scenes found for this field in the current season.")

    latest_img, latest_date, latest_cloud = latest
    clear_latest = _mask_s2(latest_img)

    compare_start = max(sowing_date, latest_date - timedelta(days=45))
    earlier = _latest_clear_scene(region, compare_start, latest_date - timedelta(days=7), before=latest_date)

    ndvi_delta = None
    compare_scene = None
    if earlier:
        earlier_img, earlier_date, earlier_cloud = earlier
        clear_earlier = _mask_s2(earlier_img)
        compare_scene = _pack_scene(clear_earlier, region, earlier_date, earlier_cloud)
        _, _, _, latest_ndvi = _sample_arrays(clear_latest, region)
        _, _, _, earlier_ndvi = _sample_arrays(clear_earlier, region)
        latest_mean = _scene_stats(latest_ndvi)["ndvi_mean"]
        earlier_mean = _scene_stats(earlier_ndvi)["ndvi_mean"]
        if latest_mean is not None and earlier_mean is not None:
            ndvi_delta = round(latest_mean - earlier_mean, 4)

    return {
        "source": "gee_sentinel2",
        "latest": _pack_scene(clear_latest, region, latest_date, latest_cloud),
        "compare": compare_scene,
        "ndvi_delta": ndvi_delta,
        "tile_url_template": None,
    }
