"""Google Earth Engine — Tier 3 Sentinel-1/2 + CHIRPS (FR-3.1, FR-3.5–3.7)."""

from __future__ import annotations

import logging
import time
from datetime import date, timedelta

from shapely import wkt as parse_wkt
from pathlib import Path

from app.core.config import get_settings
from app.services.tiers.base import RainfallContext, TierReading
from app.services.vegetation_index import sar_index_from_vv_db

logger = logging.getLogger(__name__)

_GEE_INITIALIZED = False

_GEE_MAX_RETRIES = 2
_GEE_RETRY_BACKOFF_SECONDS = 1.5

_HEALTH_PROBE_TTL_SECONDS = 60
_health_probe_cache: dict | None = None
_health_probe_cached_at = 0.0


class GEEError(RuntimeError):
    """Raised when GEE is configured but a request fails."""


def is_gee_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.gee_service_account_email
        and settings.resolved_gee_key_path
        and Path(settings.resolved_gee_key_path).is_file()
    )


def _wkt_to_ee_geometry(boundary_wkt: str):
    import ee

    geom = parse_wkt.loads(boundary_wkt)
    return ee.Geometry(geom.__geo_interface__)


def _ensure_gee_initialized() -> None:
    global _GEE_INITIALIZED
    if _GEE_INITIALIZED:
        return

    import ee

    settings = get_settings()
    if not is_gee_configured():
        raise GEEError("GEE credentials not configured (GEE_SERVICE_ACCOUNT_EMAIL + GEE_PRIVATE_KEY_PATH)")

    credentials = ee.ServiceAccountCredentials(
        settings.gee_service_account_email,
        settings.resolved_gee_key_path,
    )
    init_kwargs: dict = {"credentials": credentials}
    if settings.gee_project:
        init_kwargs["project"] = settings.gee_project
    ee.Initialize(**init_kwargs)
    _GEE_INITIALIZED = True
    logger.info("Google Earth Engine initialized for Tier 3 pipeline")


def _sar_index_from_vv_db(vv_db: float) -> float:
    """Map Sentinel-1 VV backscatter (dB) to ~0–1 index for risk engine parity."""
    return sar_index_from_vv_db(vv_db)


def _end_date_exclusive(end: date) -> str:
    return (end + timedelta(days=1)).isoformat()


def _get_info(ee_object, *, context: str):
    """Call .getInfo() with a small bounded retry for transient failures
    (timeouts, rate limits) — a single flaky call shouldn't fail a whole
    tier fetch. Not used for the health probe, which should reflect the
    current live state immediately rather than mask it behind retries."""
    last_exc: Exception | None = None
    for attempt in range(_GEE_MAX_RETRIES + 1):
        try:
            return ee_object.getInfo()
        except Exception as exc:
            last_exc = exc
            if attempt >= _GEE_MAX_RETRIES:
                break
            wait = _GEE_RETRY_BACKOFF_SECONDS * (2**attempt)
            logger.warning(
                "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                context, attempt + 1, _GEE_MAX_RETRIES + 1, exc, wait,
            )
            time.sleep(wait)
    raise GEEError(f"{context} failed after {_GEE_MAX_RETRIES + 1} attempts: {last_exc}") from last_exc


def gee_health_probe() -> dict:
    """Lightweight GEE connectivity check, cached for a short TTL rather than
    forever — a real health check should recover once GEE (or credentials)
    come back, not keep reporting the first-ever result for the process
    lifetime."""
    global _health_probe_cache, _health_probe_cached_at
    now = time.monotonic()
    if _health_probe_cache is not None and (now - _health_probe_cached_at) < _HEALTH_PROBE_TTL_SECONDS:
        return _health_probe_cache
    result = _run_gee_health_probe()
    _health_probe_cache = result
    _health_probe_cached_at = now
    return result


def _run_gee_health_probe() -> dict:
    result = {
        "configured": is_gee_configured(),
        "initialized": False,
        "connection": "not_configured",
        "message": "",
    }
    if not result["configured"]:
        result["message"] = "Set GEE_SERVICE_ACCOUNT_EMAIL and GEE_PRIVATE_KEY_PATH in backend/.env"
        return result

    try:
        import ee

        _ensure_gee_initialized()
        # Tiny probe over Matiari district centroid
        region = ee.Geometry.Point([68.45, 25.6])
        count = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate("2024-01-01", "2024-02-01")
            .size()
            .getInfo()
        )
        result["initialized"] = True
        result["connection"] = "ok"
        result["message"] = f"S2 collection reachable ({count} scenes in probe window)"
    except Exception as exc:
        result["connection"] = "error"
        result["message"] = str(exc)
    return result


def fetch_tier3_from_gee(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    import ee

    _ensure_gee_initialized()
    end = season_end or date.today()
    region = _wkt_to_ee_geometry(boundary_wkt)
    end_exclusive = _end_date_exclusive(end)
    optical_scale = 10
    sar_scale = 10

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(sowing_date.isoformat(), end_exclusive)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60))
        .sort("system:time_start")
    )

    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(region)
        .filterDate(sowing_date.isoformat(), end_exclusive)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .select("VV")
        .sort("system:time_start")
    )

    def optical_feature(img: ee.Image) -> ee.Feature:
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
        evi = img.expression(
            "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
            {"NIR": img.select("B8"), "RED": img.select("B4"), "BLUE": img.select("B2")},
        ).rename("EVI")
        combined = ndvi.addBands(evi)
        stats = combined.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=optical_scale,
            maxPixels=1e9,
            bestEffort=True,
        )
        return ee.Feature(None, {
            "date": img.date().format("YYYY-MM-dd"),
            "ndvi": stats.get("NDVI"),
            "evi": stats.get("EVI"),
            "cloud": img.get("CLOUDY_PIXEL_PERCENTAGE"),
        })

    def sar_feature(img: ee.Image) -> ee.Feature:
        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=sar_scale,
            maxPixels=1e9,
            bestEffort=True,
        )
        return ee.Feature(None, {
            "date": img.date().format("YYYY-MM-dd"),
            "vv_db": stats.get("VV"),
        })

    optical_feats = _get_info(s2.map(optical_feature), context="Tier 3 Sentinel-2 fetch").get("features", [])
    sar_feats = _get_info(s1.map(sar_feature), context="Tier 3 Sentinel-1 fetch").get("features", [])

    by_date: dict[date, TierReading] = {}

    for feat in optical_feats:
        props = feat.get("properties", {})
        date_str = props.get("date")
        if not date_str:
            continue
        acq = date.fromisoformat(date_str)
        ndvi_raw = props.get("ndvi")
        evi_raw = props.get("evi")
        cloud_raw = props.get("cloud")
        by_date[acq] = TierReading(
            acquisition_date=acq,
            ndvi=round(float(ndvi_raw), 5) if ndvi_raw is not None else None,
            evi=round(float(evi_raw), 5) if evi_raw is not None else None,
            cloud_fraction=round(float(cloud_raw) / 100.0, 4) if cloud_raw is not None else None,
        )

    for feat in sar_feats:
        props = feat.get("properties", {})
        date_str = props.get("date")
        vv_db = props.get("vv_db")
        if not date_str or vv_db is None:
            continue
        acq = date.fromisoformat(date_str)
        sar_idx = _sar_index_from_vv_db(float(vv_db))
        existing = by_date.get(acq)
        if existing:
            existing.sar_index = sar_idx
        else:
            by_date[acq] = TierReading(
                acquisition_date=acq,
                sar_index=sar_idx,
                cloud_fraction=0.0,
            )

    readings = sorted(by_date.values(), key=lambda r: r.acquisition_date)
    if not readings:
        raise GEEError(
            "No Sentinel-1 or Sentinel-2 scenes found for this field and date range. "
            "Try a later sowing date or verify the AOI is within Matiari coverage."
        )
    return readings


def fetch_tier2_composite_from_gee(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    """Tier 2 — weekly cloud-masked Sentinel-2 median composites (M4 GEE path)."""
    import ee

    _ensure_gee_initialized()
    end = season_end or date.today()
    region = _wkt_to_ee_geometry(boundary_wkt)
    readings: list[TierReading] = []
    week_start = sowing_date

    def mask_s2(img: ee.Image) -> ee.Image:
        scl = img.select("SCL")
        clear = (
            scl.neq(3)
            .And(scl.neq(8))
            .And(scl.neq(9))
            .And(scl.neq(10))
        )
        return img.updateMask(clear)

    while week_start <= end:
        week_end = min(week_start + timedelta(days=6), end)
        end_exclusive = _end_date_exclusive(week_end)
        coll = (
            ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(region)
            .filterDate(week_start.isoformat(), end_exclusive)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 25))
            .map(mask_s2)
        )
        count = _get_info(coll.size(), context="Tier 2 weekly composite count")
        if count == 0:
            week_start += timedelta(days=7)
            continue

        composite = coll.median()
        ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")
        evi = composite.expression(
            "2.5 * ((NIR - RED) / (NIR + 6 * RED - 7.5 * BLUE + 1))",
            {"NIR": composite.select("B8"), "RED": composite.select("B4"), "BLUE": composite.select("B2")},
        ).rename("EVI")
        stats = _get_info(
            ndvi.addBands(evi).reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=10,
                maxPixels=1e9,
                bestEffort=True,
            ),
            context="Tier 2 weekly composite stats",
        )

        ndvi_val = stats.get("NDVI")
        if ndvi_val is not None:
            readings.append(
                TierReading(
                    acquisition_date=week_end,
                    ndvi=round(float(ndvi_val), 5),
                    evi=round(float(stats.get("EVI", ndvi_val)), 5),
                    cloud_fraction=0.0,
                )
            )
        week_start += timedelta(days=7)

    if not readings:
        raise GEEError("No clear Sentinel-2 composites found for Tier 2 in this date range.")
    return readings


def fetch_chirps_rainfall(boundary_wkt: str, start: date, end: date) -> RainfallContext:
    import ee

    _ensure_gee_initialized()
    region = _wkt_to_ee_geometry(boundary_wkt)
    end_exclusive = _end_date_exclusive(end)

    period_coll = (
        ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
        .filterDate(start.isoformat(), end_exclusive)
        .select("precipitation")
    )
    period_mm = float(
        _get_info(
            period_coll.sum().reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=5566,
                maxPixels=1e9,
                bestEffort=True,
            ).get("precipitation"),
            context="CHIRPS period rainfall",
        )
        or 0
    )

    # Historical: same calendar window in prior years (up to 5 years back)
    hist_totals: list[float] = []
    for years_back in range(1, 6):
        try:
            hist_start = start.replace(year=start.year - years_back)
            hist_end = end.replace(year=end.year - years_back)
        except ValueError:
            continue
        hist_coll = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterDate(hist_start.isoformat(), _end_date_exclusive(hist_end))
            .select("precipitation")
        )
        hist_val = _get_info(
            hist_coll.sum().reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=region,
                scale=5566,
                maxPixels=1e9,
                bestEffort=True,
            ).get("precipitation"),
            context=f"CHIRPS historical rainfall ({years_back}y back)",
        )
        if hist_val is not None:
            hist_totals.append(float(hist_val))

    historical_mean = sum(hist_totals) / len(hist_totals) if hist_totals else period_mm
    anomaly_pct = ((period_mm - historical_mean) / max(historical_mean, 0.1)) * 100

    return RainfallContext(
        period_mm=round(period_mm, 2),
        historical_mean_mm=round(historical_mean, 2),
        anomaly_pct=round(anomaly_pct, 2),
    )
