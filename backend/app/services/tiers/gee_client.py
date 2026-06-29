"""Google Earth Engine — Tier 3 Sentinel-1/2 + CHIRPS (FR-3.1, FR-3.5–3.7)."""

from __future__ import annotations

import logging
from datetime import date, timedelta
from functools import lru_cache

from shapely import wkt as parse_wkt

from app.core.config import get_settings
from app.services.tiers.base import RainfallContext, TierReading

logger = logging.getLogger(__name__)

_GEE_INITIALIZED = False


class GEEError(RuntimeError):
    """Raised when GEE is configured but a request fails."""


def is_gee_configured() -> bool:
    settings = get_settings()
    return bool(settings.gee_service_account_email and settings.gee_private_key_path)


def _wkt_to_ee_geometry(boundary_wkt: str):
    import ee

    geom = parse_wkt.loads(boundary_wkt)
    if geom.geom_type != "Polygon":
        raise ValueError("Field boundary must be a Polygon for GEE extraction")
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
        settings.gee_private_key_path,
    )
    init_kwargs: dict = {"credentials": credentials}
    if settings.gee_project:
        init_kwargs["project"] = settings.gee_project
    ee.Initialize(**init_kwargs)
    _GEE_INITIALIZED = True
    logger.info("Google Earth Engine initialized for Tier 3 pipeline")


def _sar_index_from_vv_db(vv_db: float) -> float:
    """Map Sentinel-1 VV backscatter (dB) to ~0–1 index for risk engine parity."""
    return round(max(0.0, min(1.0, (vv_db + 22.0) / 18.0)), 5)


def _end_date_exclusive(end: date) -> str:
    return (end + timedelta(days=1)).isoformat()


@lru_cache(maxsize=1)
def gee_health_probe() -> dict:
    """Lightweight GEE connectivity check (cached per process)."""
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

    optical_feats = s2.map(optical_feature).getInfo().get("features", [])
    sar_feats = s1.map(sar_feature).getInfo().get("features", [])

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
        period_coll.sum().reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=5566,
            maxPixels=1e9,
            bestEffort=True,
        ).get("precipitation").getInfo()
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
        hist_val = hist_coll.sum().reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=5566,
            maxPixels=1e9,
            bestEffort=True,
        ).get("precipitation").getInfo()
        if hist_val is not None:
            hist_totals.append(float(hist_val))

    historical_mean = sum(hist_totals) / len(hist_totals) if hist_totals else period_mm
    anomaly_pct = ((period_mm - historical_mean) / max(historical_mean, 0.1)) * 100

    return RainfallContext(
        period_mm=round(period_mm, 2),
        historical_mean_mm=round(historical_mean, 2),
        anomaly_pct=round(anomaly_pct, 2),
    )
