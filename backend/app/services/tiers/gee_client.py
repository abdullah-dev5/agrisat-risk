"""Google Earth Engine integration for Tier 3 (FR-3.1).

Install earthengine-api and configure GEE_SERVICE_ACCOUNT_EMAIL + GEE_PRIVATE_KEY_PATH.
"""

from datetime import date, timedelta

from app.services.tiers.base import TierReading, RainfallContext


def _ensure_gee_initialized() -> None:
    import ee
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.gee_service_account_email or not settings.gee_private_key_path:
        raise RuntimeError("GEE credentials not configured")

    credentials = ee.ServiceAccountCredentials(
        settings.gee_service_account_email,
        settings.gee_private_key_path,
    )
    ee.Initialize(credentials)


def fetch_tier3_from_gee(
    boundary_wkt: str,
    sowing_date: date,
    season_end: date | None = None,
) -> list[TierReading]:
    import ee

    _ensure_gee_initialized()
    end = season_end or date.today()
    region = ee.Geometry(boundary_wkt)

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(sowing_date.isoformat(), end.isoformat())
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
    )

    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(region)
        .filterDate(sowing_date.isoformat(), end.isoformat())
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
    )

    def ndvi_from_s2(img: ee.Image) -> ee.Feature:
        ndvi = img.normalizedDifference(["B8", "B4"]).rename("NDVI")
        stats = ndvi.reduceRegion(ee.Reducer.mean(), region, 10)
        return ee.Feature(None, {
            "date": img.date().format("YYYY-MM-dd"),
            "ndvi": stats.get("NDVI"),
            "cloud": img.get("CLOUDY_PIXEL_PERCENTAGE"),
        })

    def sar_from_s1(img: ee.Image) -> ee.Feature:
        vv = img.select("VV").reduceRegion(ee.Reducer.mean(), region, 10)
        return ee.Feature(None, {
            "date": img.date().format("YYYY-MM-dd"),
            "sar": vv.get("VV"),
        })

    optical_feats = s2.map(ndvi_from_s2).getInfo()["features"]
    sar_feats = s1.map(sar_from_s1).getInfo()["features"]

    sar_by_date = {f["properties"]["date"]: f["properties"].get("sar") for f in sar_feats}
    readings: list[TierReading] = []

    for feat in optical_feats:
        props = feat["properties"]
        acq = date.fromisoformat(props["date"])
        ndvi_val = props.get("ndvi")
        readings.append(
            TierReading(
                acquisition_date=acq,
                ndvi=float(ndvi_val) if ndvi_val is not None else None,
                cloud_fraction=float(props.get("cloud", 0)) / 100.0,
            )
        )

    for acq_str, sar_val in sar_by_date.items():
        if sar_val is None:
            continue
        acq = date.fromisoformat(acq_str)
        if not any(r.acquisition_date == acq for r in readings):
            readings.append(
                TierReading(acquisition_date=acq, sar_index=float(sar_val), cloud_fraction=0.0)
            )

    readings.sort(key=lambda r: r.acquisition_date)
    return readings


def fetch_chirps_rainfall(boundary_wkt: str, start: date, end: date) -> RainfallContext:
    import ee

    _ensure_gee_initialized()
    region = ee.Geometry(boundary_wkt)

    chirps = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(
        start.isoformat(), end.isoformat()
    )
    total = chirps.select("precipitation").sum().reduceRegion(ee.Reducer.mean(), region, 5000)
    period_mm = float(total.get("precipitation").getInfo() or 0)

    hist_start = start.replace(year=start.year - 5)
    hist = ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY").filterDate(
        hist_start.isoformat(), end.replace(year=end.year - 1).isoformat()
    )
    hist_mean = hist.select("precipitation").mean().reduceRegion(ee.Reducer.mean(), region, 5000)
    historical_mean = float(hist_mean.get("precipitation").getInfo() or 1) * (end - start).days

    anomaly_pct = ((period_mm - historical_mean) / max(historical_mean, 1)) * 100
    return RainfallContext(period_mm=period_mm, historical_mean_mm=historical_mean, anomaly_pct=anomaly_pct)
