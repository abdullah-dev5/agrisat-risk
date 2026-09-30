"""GEE field imagery — latest RGB + NDVI previews for growth monitoring."""

from __future__ import annotations

import base64
import io
import logging
from datetime import date, timedelta
from typing import Any

import numpy as np
import pyproj
from PIL import Image, ImageFilter
from shapely import wkt as shapely_wkt
from shapely.ops import transform as shapely_transform

from app.services.tiers.gee_client import GEEError, _ensure_gee_initialized, _wkt_to_ee_geometry, is_gee_configured

logger = logging.getLogger(__name__)

NDVI_MIN = 0.0
NDVI_MAX = 0.85
NDVI_PALETTE = ("#a50026", "#fee08b", "#006837")

# Sentinel-2's visible bands are natively ~10m/pixel. Sampling a small field
# at that scale directly (the old behavior) can yield an array as small as a
# few dozen pixels per side -- converted straight to a PNG with no
# upscaling, that reads as "blurry" once the browser stretches it to fill a
# normal display size. Fixed by resampling server-side (in GEE, with proper
# interpolation, not by hallucinating detail) to a finer scale chosen from
# the field's own footprint, then a final client-side resize + mild
# sharpening pass. This is display-quality processing, not synthetic
# super-resolution: it makes the real pixels look smooth and properly
# contrasted, it doesn't invent detail that isn't in the source data.
NATIVE_SCALE_M = 10.0
MIN_SAMPLE_SCALE_M = 2.5
TARGET_OUTPUT_PX = 480
MAX_OUTPUT_PX = 720
STRETCH_LOW_PCT = 2.0
STRETCH_HIGH_PCT = 98.0


def _display_scale_m(boundary_wkt: str) -> float:
    """Pick a GEE sampling scale (meters/pixel) so the output has roughly
    TARGET_OUTPUT_PX pixels on its longer side, without resampling finer
    than MIN_SAMPLE_SCALE_M (diminishing returns past that -- Sentinel-2
    doesn't have more real detail to give no matter how fine you resample)
    or coarser than the sensor's own native resolution."""
    geom = shapely_wkt.loads(boundary_wkt)
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    minx, miny, maxx, maxy = shapely_transform(project, geom).bounds
    span_m = max(maxx - minx, maxy - miny, 1.0)
    scale = span_m / TARGET_OUTPUT_PX
    return max(MIN_SAMPLE_SCALE_M, min(scale, NATIVE_SCALE_M))


def _percentile_stretch(arr: np.ndarray, low_pct: float = STRETCH_LOW_PCT, high_pct: float = STRETCH_HIGH_PCT) -> np.ndarray:
    """Per-band linear contrast stretch to this scene's own 2nd-98th
    percentile reflectance range, the standard remote-sensing visualization
    technique -- rather than a single fixed reflectance window that looks
    over- or under-exposed depending on what's actually in the scene
    (bright bare soil vs. dense canopy vs. water all sit in very different
    reflectance ranges)."""
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        return np.zeros_like(arr)
    lo, hi = np.percentile(valid, [low_pct, high_pct])
    if hi <= lo:
        hi = lo + 1.0
    return np.clip((arr - lo) / (hi - lo) * 255, 0, 255)


def _finalize_image(rgb_uint8: np.ndarray) -> Image.Image:
    """Resize to a consistent, display-ready size with high-quality
    interpolation, then a light unsharp-mask pass. Both steps work on
    pixels already sampled from the real scene -- this sharpens/smooths
    existing values, it doesn't add information that wasn't there."""
    img = Image.fromarray(rgb_uint8, mode="RGB")
    longer_side = max(img.width, img.height)
    target = max(TARGET_OUTPUT_PX, min(longer_side, MAX_OUTPUT_PX))
    if longer_side != target:
        ratio = target / longer_side
        new_size = (max(1, round(img.width * ratio)), max(1, round(img.height * ratio)))
        img = img.resize(new_size, Image.LANCZOS)
    return img.filter(ImageFilter.UnsharpMask(radius=1.6, percent=110, threshold=2))


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


def _to_data_url(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _sample_arrays(clear_img, region, scale_m: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    stacked = clear_img.select(["B4", "B3", "B2"]).addBands(
        clear_img.normalizedDifference(["B8", "B4"]).rename("NDVI")
    )
    # Resample (bicubic, i.e. smooth interpolation of the real reflectance
    # values -- not a learned/hallucinated reconstruction) and reproject to
    # a finer scale before sampling, so the output has enough real pixels to
    # look smooth once displayed instead of a handful of native 10m blocks
    # stretched to fill the screen. See _display_scale_m's docstring.
    proj = clear_img.select("B4").projection()
    resampled = stacked.resample("bicubic").reproject(crs=proj, scale=scale_m)
    props = resampled.sampleRectangle(region=region, defaultValue=0).getInfo()["properties"]
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
    rgb = np.stack([_percentile_stretch(r), _percentile_stretch(g), _percentile_stretch(b)], axis=-1)
    return _to_data_url(_finalize_image(rgb.astype(np.uint8)))


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
    return _to_data_url(_finalize_image(rgb.astype(np.uint8)))


def _scene_stats(ndvi: np.ndarray) -> dict[str, float | None]:
    valid = ndvi[np.isfinite(ndvi) & (ndvi > -1) & (ndvi < 1)]
    if valid.size == 0:
        return {"ndvi_mean": None}
    return {"ndvi_mean": round(float(valid.mean()), 4)}


def _pack_scene(acq: date, cloud_pct: float, r: np.ndarray, g: np.ndarray, b: np.ndarray, ndvi: np.ndarray) -> dict[str, Any]:
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
    scale_m = _display_scale_m(boundary_wkt)

    latest = _latest_clear_scene(region, sowing_date, end)
    if not latest:
        raise GEEError("No clear Sentinel-2 scenes found for this field in the current season.")

    latest_img, latest_date, latest_cloud = latest
    clear_latest = _mask_s2(latest_img)
    latest_r, latest_g, latest_b, latest_ndvi = _sample_arrays(clear_latest, region, scale_m)
    latest_scene = _pack_scene(latest_date, latest_cloud, latest_r, latest_g, latest_b, latest_ndvi)

    compare_start = max(sowing_date, latest_date - timedelta(days=45))
    earlier = _latest_clear_scene(region, compare_start, latest_date - timedelta(days=7), before=latest_date)

    ndvi_delta = None
    compare_scene = None
    if earlier:
        earlier_img, earlier_date, earlier_cloud = earlier
        clear_earlier = _mask_s2(earlier_img)
        earlier_r, earlier_g, earlier_b, earlier_ndvi = _sample_arrays(clear_earlier, region, scale_m)
        compare_scene = _pack_scene(earlier_date, earlier_cloud, earlier_r, earlier_g, earlier_b, earlier_ndvi)
        latest_mean = _scene_stats(latest_ndvi)["ndvi_mean"]
        earlier_mean = _scene_stats(earlier_ndvi)["ndvi_mean"]
        if latest_mean is not None and earlier_mean is not None:
            ndvi_delta = round(latest_mean - earlier_mean, 4)

    return {
        "source": "gee_sentinel2",
        "latest": latest_scene,
        "compare": compare_scene,
        "ndvi_delta": ndvi_delta,
        "tile_url_template": None,
    }
