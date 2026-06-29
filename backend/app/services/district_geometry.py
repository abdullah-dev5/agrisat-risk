"""Pilot district geometry helpers (M7)."""

from __future__ import annotations

from shapely.geometry import Polygon

from app.core.config import Settings


def pilot_district_wkt(settings: Settings) -> str:
    """Convert PILOT_REGION_BBOX (min_lng,min_lat,max_lng,max_lat) to WKT polygon."""
    parts = [float(x.strip()) for x in settings.pilot_region_bbox.split(",")]
    if len(parts) != 4:
        raise ValueError("PILOT_REGION_BBOX must be min_lng,min_lat,max_lng,max_lat")
    min_lng, min_lat, max_lng, max_lat = parts
    ring = [
        (min_lng, min_lat),
        (max_lng, min_lat),
        (max_lng, max_lat),
        (min_lng, max_lat),
        (min_lng, min_lat),
    ]
    return Polygon(ring).wkt
