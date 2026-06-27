"""Geometry helpers for field boundary validation (FR-2.5)."""

from typing import Any

from shapely.geometry import shape
from shapely.ops import transform
import pyproj

from app.core.config import Settings


def geojson_to_wkt(geojson: dict[str, Any]) -> str:
    geom = shape(geojson)
    if geom.geom_type != "Polygon":
        raise ValueError("Field boundary must be a Polygon")
    return geom.wkt


def compute_area_hectares(geojson: dict[str, Any]) -> float:
    geom = shape(geojson)
    project = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True).transform
    projected = transform(project, geom)
    return projected.area / 10_000


def validate_field_area(area_hectares: float, settings: Settings) -> bool:
    """Returns True if area is below minimum threshold (resolution warning)."""
    return area_hectares < settings.min_field_hectares


def geojson_polygon(geojson: dict[str, Any]) -> dict[str, Any]:
    geom = shape(geojson)
    if geom.geom_type != "Polygon":
        raise ValueError("Field boundary must be a Polygon")
    if not geom.is_valid:
        geom = geom.buffer(0)
    return {"type": "Polygon", "coordinates": [list(geom.exterior.coords)]}
