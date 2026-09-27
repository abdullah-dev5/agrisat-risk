import pytest

from app.core.config import Settings
from app.services.geometry import (
    geojson_to_wkt,
    compute_area_hectares,
    validate_field_area,
    geojson_polygon,
)

# A small rectangle near Matiari, Sindh (~68.4-68.41 lng, 25.6-25.61 lat) --
# roughly 1 hectare, used only to sanity-check the math, not for precision.
SQUARE_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [68.40, 25.60],
        [68.41, 25.60],
        [68.41, 25.61],
        [68.40, 25.61],
        [68.40, 25.60],
    ]],
}

LINESTRING_GEOJSON = {"type": "LineString", "coordinates": [[68.40, 25.60], [68.41, 25.61]]}


def test_geojson_to_wkt_accepts_a_polygon():
    wkt = geojson_to_wkt(SQUARE_GEOJSON)
    assert wkt.startswith("POLYGON")


def test_geojson_to_wkt_rejects_non_polygon():
    with pytest.raises(ValueError, match="must be a Polygon"):
        geojson_to_wkt(LINESTRING_GEOJSON)


def test_compute_area_hectares_is_positive_and_plausible():
    area = compute_area_hectares(SQUARE_GEOJSON)
    # ~0.01deg square near the equator-ish latitude is on the order of 100 ha,
    # not thousands or a fraction of one -- a loose sanity bound, not a precise check.
    assert 10 < area < 1000


def test_validate_field_area_flags_below_minimum():
    settings = Settings(min_field_hectares=0.2)
    assert validate_field_area(0.1, settings) is True
    assert validate_field_area(5.0, settings) is False


def test_geojson_polygon_returns_polygon_shape():
    result = geojson_polygon(SQUARE_GEOJSON)
    assert result["type"] == "Polygon"
    assert len(result["coordinates"][0]) >= 4


def test_geojson_polygon_rejects_non_polygon():
    with pytest.raises(ValueError, match="must be a Polygon"):
        geojson_polygon(LINESTRING_GEOJSON)
