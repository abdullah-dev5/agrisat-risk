"""Regression test for crop_type validation (docs/AUDIT-FINDINGS.md #12).

Confirmed live before writing this fix: scripts/build_district_baseline.py
only ever builds a baseline for settings.pilot_crop, and every row in the
real baseline_stats table is crop_type='wheat' -- there is no path by which
a baseline for any other crop could exist. So accepting an arbitrary
crop_type at field creation isn't a genuine multi-crop capability, it's a
silent trap: the field gets created, a real GEE job runs (real cost, real
quota), and the result is just INSUFFICIENT_DATA. Rejecting it immediately
with a clear message is strictly better for the same outcome.
"""
from datetime import date

import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.schemas.domain import FieldCreateRequest
from app.services import field_service


def test_validate_crop_type_accepts_the_pilot_crop():
    settings = Settings(pilot_crop="wheat")
    field_service._validate_crop_type("wheat", settings)  # should not raise


def test_validate_crop_type_is_case_insensitive():
    settings = Settings(pilot_crop="wheat")
    field_service._validate_crop_type("Wheat", settings)
    field_service._validate_crop_type("WHEAT", settings)


def test_validate_crop_type_rejects_anything_else():
    settings = Settings(pilot_crop="wheat")
    with pytest.raises(HTTPException) as exc_info:
        field_service._validate_crop_type("rice", settings)
    assert exc_info.value.status_code == 400
    assert "wheat" in exc_info.value.detail
    assert "rice" in exc_info.value.detail


def test_create_field_rejects_wrong_crop_type_before_touching_gee_or_supabase(monkeypatch):
    # If validation didn't short-circuit first, this would blow up on the
    # missing Supabase/GEE setup rather than cleanly reject the crop_type --
    # asserting HTTPException 400 here proves it fails fast, before any of
    # that.
    monkeypatch.setattr(
        field_service, "get_supabase_admin", lambda: (_ for _ in ()).throw(AssertionError("should not be called"))
    )
    payload = FieldCreateRequest(
        boundary_geojson={},  # deliberately invalid -- proves crop check runs first
        crop_type="rice",
        sowing_date=date(2025, 11, 15),
    )
    with pytest.raises(HTTPException) as exc_info:
        field_service.create_field(payload, "institution-A", "user-A", Settings(pilot_crop="wheat"))
    assert exc_info.value.status_code == 400
    assert "rice" in exc_info.value.detail
