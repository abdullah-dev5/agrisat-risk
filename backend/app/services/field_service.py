"""Field CRUD and processing orchestration."""

from datetime import date
from typing import Any

from fastapi import HTTPException, status

from app.core.config import Settings
from app.core.supabase_client import get_supabase_admin
from app.schemas.domain import FieldCreateRequest, FieldResponse, FieldUpdateRequest
from app.services.baseline import generate_demo_baseline
from app.services.fusion import FusedReading, select_and_fuse
from app.services.geometry import compute_area_hectares, geojson_polygon, geojson_to_wkt, validate_field_area
from app.services.risk_engine import assess_risk


def _boundary_from_row(row: dict) -> dict[str, Any]:
    if isinstance(row.get("boundary"), dict):
        return row["boundary"]
    return row.get("boundary_geojson", {"type": "Polygon", "coordinates": []})


def _field_response(row: dict, risk_tier: str | None = None) -> FieldResponse:
    return FieldResponse(
        id=row["id"],
        institution_id=row["institution_id"],
        name=row.get("name"),
        boundary_geojson=_boundary_from_row(row),
        area_hectares=float(row["area_hectares"]) if row.get("area_hectares") else None,
        crop_type=row["crop_type"],
        sowing_date=date.fromisoformat(str(row["sowing_date"])),
        farmer_ref_id=row.get("farmer_ref_id"),
        loan_ref_id=row.get("loan_ref_id"),
        status=row["status"],
        resolution_warning=row.get("resolution_warning", False),
        pilot_district=row.get("pilot_district", "faisalabad"),
        current_risk_tier=risk_tier,
        created_at=row["created_at"],
    )


def create_field(
    payload: FieldCreateRequest,
    institution_id: str,
    user_id: str,
    settings: Settings,
) -> FieldResponse:
    try:
        geojson = geojson_polygon(payload.boundary_geojson)
        area = compute_area_hectares(geojson)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if area > settings.max_field_hectares:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Field area exceeds maximum threshold")

    resolution_warning = validate_field_area(area, settings)
    sb = get_supabase_admin()

    insert_data = {
        "institution_id": institution_id,
        "created_by": user_id,
        "name": payload.name,
        "boundary": geojson,
        "area_hectares": round(area, 4),
        "crop_type": payload.crop_type,
        "sowing_date": payload.sowing_date.isoformat(),
        "farmer_ref_id": payload.farmer_ref_id,
        "loan_ref_id": payload.loan_ref_id,
        "resolution_warning": resolution_warning,
        "pilot_district": settings.pilot_district,
    }

    resp = sb.table("fields").insert(insert_data).execute()
    row = resp.data[0]
    process_field(row["id"], settings)
    return get_field(row["id"], institution_id)


def get_field(field_id: str, institution_id: str) -> FieldResponse:
    sb = get_supabase_admin()
    resp = sb.table("fields").select("*").eq("id", field_id).eq("institution_id", institution_id).single().execute()
    if not resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")

    risk_resp = (
        sb.table("risk_assessments")
        .select("risk_tier")
        .eq("field_id", field_id)
        .eq("is_current", True)
        .limit(1)
        .execute()
    )
    risk_tier = risk_resp.data[0]["risk_tier"] if risk_resp.data else None
    return _field_response(resp.data, risk_tier)


def list_fields(institution_id: str, status_filter: str | None = "active") -> list[FieldResponse]:
    sb = get_supabase_admin()
    query = sb.table("fields").select("*").eq("institution_id", institution_id)
    if status_filter:
        query = query.eq("status", status_filter)
    resp = query.order("created_at", desc=True).execute()

    field_ids = [r["id"] for r in resp.data]
    risk_map: dict[str, str] = {}
    if field_ids:
        risk_resp = (
            sb.table("risk_assessments")
            .select("field_id, risk_tier")
            .in_("field_id", field_ids)
            .eq("is_current", True)
            .execute()
        )
        risk_map = {r["field_id"]: r["risk_tier"] for r in risk_resp.data}

    return [_field_response(r, risk_map.get(r["id"])) for r in resp.data]


def update_field(
    field_id: str,
    payload: FieldUpdateRequest,
    institution_id: str,
    settings: Settings,
) -> FieldResponse:
    sb = get_supabase_admin()
    existing = sb.table("fields").select("*").eq("id", field_id).eq("institution_id", institution_id).single().execute()
    if not existing.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")

    updates: dict[str, Any] = {}
    if payload.name is not None:
        updates["name"] = payload.name
    if payload.crop_type is not None:
        updates["crop_type"] = payload.crop_type
    if payload.sowing_date is not None:
        updates["sowing_date"] = payload.sowing_date.isoformat()
    if payload.farmer_ref_id is not None:
        updates["farmer_ref_id"] = payload.farmer_ref_id
    if payload.loan_ref_id is not None:
        updates["loan_ref_id"] = payload.loan_ref_id
    if payload.status is not None:
        updates["status"] = payload.status.value
    if payload.boundary_geojson is not None:
        geojson = geojson_polygon(payload.boundary_geojson)
        area = compute_area_hectares(geojson)
        updates["boundary"] = geojson
        updates["area_hectares"] = round(area, 4)
        updates["resolution_warning"] = validate_field_area(area, settings)

    if updates:
        sb.table("fields").update(updates).eq("id", field_id).execute()
        if any(k in updates for k in ("boundary", "sowing_date", "crop_type")):
            process_field(field_id, settings)

    return get_field(field_id, institution_id)


def get_field_detail(field_id: str, institution_id: str) -> dict:
    sb = get_supabase_admin()
    field_resp = sb.table("fields").select("*").eq("id", field_id).eq("institution_id", institution_id).single().execute()
    if not field_resp.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")

    readings = (
        sb.table("vegetation_readings")
        .select("*")
        .eq("field_id", field_id)
        .order("acquisition_date")
        .execute()
        .data
    )
    baseline = (
        sb.table("baseline_stats")
        .select("*")
        .eq("crop_type", field_resp.data["crop_type"])
        .eq("pilot_district", field_resp.data["pilot_district"])
        .order("days_since_sowing")
        .execute()
        .data
    )
    assessment = (
        sb.table("risk_assessments")
        .select("*")
        .eq("field_id", field_id)
        .eq("is_current", True)
        .limit(1)
        .execute()
        .data
    )

    risk_tier = assessment[0]["risk_tier"] if assessment else None
    return {
        "field": _field_response(field_resp.data, risk_tier),
        "vegetation_readings": readings,
        "baseline": baseline,
        "current_assessment": assessment[0] if assessment else None,
    }


def process_field(field_id: str, settings: Settings) -> None:
    sb = get_supabase_admin()
    field = sb.table("fields").select("*").eq("id", field_id).single().execute().data
    sowing = date.fromisoformat(str(field["sowing_date"]))
    boundary = _boundary_from_row(field)
    wkt = geojson_to_wkt(boundary)

    fused = select_and_fuse(wkt, sowing)

    sb.table("vegetation_readings").delete().eq("field_id", field_id).execute()
    for r in fused:
        sb.table("vegetation_readings").insert({
            "field_id": field_id,
            "acquisition_date": r.acquisition_date.isoformat(),
            "days_since_sowing": r.days_since_sowing,
            "data_tier": r.data_tier.value,
            "ndvi": r.ndvi,
            "evi": r.evi,
            "sar_index": r.sar_index,
            "cloud_fraction": r.cloud_fraction,
            "is_fused": True,
        }).execute()

    baseline_rows = (
        sb.table("baseline_stats")
        .select("*")
        .eq("crop_type", field["crop_type"])
        .eq("pilot_district", field["pilot_district"])
        .execute()
        .data
    )
    if not baseline_rows:
        demo = generate_demo_baseline(settings)
        for b in demo:
            sb.table("baseline_stats").upsert({
                "crop_type": field["crop_type"],
                "pilot_district": field["pilot_district"],
                **b,
            }).execute()
        baseline_rows = demo

    rainfall_mm = None
    rainfall_anomaly_pct = None
    try:
        from app.services.tiers.gee_client import fetch_chirps_rainfall

        end = date.today()
        start = end.replace(day=1)
        ctx = fetch_chirps_rainfall(wkt, start, end)
        rainfall_mm = ctx.period_mm
        rainfall_anomaly_pct = ctx.anomaly_pct
    except Exception:
        rainfall_anomaly_pct = -25.0
        rainfall_mm = 12.0

    fused_objs = [
        FusedReading(
            acquisition_date=r.acquisition_date,
            days_since_sowing=r.days_since_sowing,
            data_tier=r.data_tier,
            ndvi=r.ndvi,
            evi=r.evi,
            sar_index=r.sar_index,
            cloud_fraction=r.cloud_fraction,
            index_value=r.index_value,
        )
        for r in fused
    ]

    result = assess_risk(fused_objs, baseline_rows, sowing, settings, rainfall_mm, rainfall_anomaly_pct)

    sb.table("risk_assessments").update({"is_current": False}).eq("field_id", field_id).execute()
    assessment = sb.table("risk_assessments").insert({
        "field_id": field_id,
        "days_since_sowing": result.days_since_sowing,
        "z_score": result.z_score,
        "risk_tier": result.risk_tier.value,
        "primary_data_tier": result.primary_data_tier.value if result.primary_data_tier else None,
        "index_value": result.index_value,
        "baseline_mean": result.baseline_mean,
        "baseline_std": result.baseline_std,
        "rainfall_mm": result.rainfall_mm,
        "rainfall_anomaly_pct": result.rainfall_anomaly_pct,
        "explanation": result.explanation,
        "is_current": True,
    }).execute().data[0]

    sb.table("risk_audit_log").insert({
        "field_id": field_id,
        "risk_assessment_id": assessment["id"],
        "event_type": "risk_assessed",
        "payload": result.audit_payload,
    }).execute()
