"""Field CRUD and processing orchestration."""

import logging
from datetime import date
from typing import Any

from fastapi import HTTPException, status

from app.core.config import Settings
from app.core.supabase_client import get_supabase_admin
from app.models.enums import DataTier
from app.schemas.domain import FieldCreateRequest, FieldResponse, FieldUpdateRequest
from app.services.baseline import build_gee_baseline
from app.services.fusion import FusedReading, FusionResult, select_and_fuse
from app.services.geometry import compute_area_hectares, geojson_polygon, geojson_to_wkt, validate_field_area
from app.services.risk_engine import assess_risk
from app.services.vegetation_index import index_family_for_tier

logger = logging.getLogger(__name__)


def _load_baselines(sb, crop_type: str, pilot_district: str) -> list[dict]:
    resp = (
        sb.table("baseline_stats")
        .select("*")
        .eq("crop_type", crop_type)
        .eq("pilot_district", pilot_district)
        .execute()
    )
    return resp.data or []


def _ensure_gee_baselines(
    sb,
    wkt: str,
    sowing: date,
    crop_type: str,
    pilot_district: str,
) -> list[dict]:
    """Build and persist live GEE baselines for crop + district."""
    from app.services.tiers.gee_client import is_gee_configured

    if not is_gee_configured():
        return _load_baselines(sb, crop_type, pilot_district)

    try:
        rows = build_gee_baseline(wkt, sowing)
    except Exception as exc:
        logger.warning("GEE baseline build failed: %s", exc)
        return _load_baselines(sb, crop_type, pilot_district)

    if not rows:
        return _load_baselines(sb, crop_type, pilot_district)

    # Replace stale demo / mismatched baselines for this crop + district
    sb.table("baseline_stats").delete().eq("crop_type", crop_type).eq(
        "pilot_district", pilot_district
    ).execute()

    for b in rows:
        payload = {"crop_type": crop_type, "pilot_district": pilot_district, **b}
        try:
            sb.table("baseline_stats").insert(payload).execute()
        except Exception as exc:
            # Pre-migration 005: one row per growth stage — keep first tier inserted (SAR listed first)
            if "23505" in str(exc):
                logger.debug("Baseline day %s tier skipped (schema upgrade 005 pending)", b.get("days_since_sowing"))
                continue
            raise

    return _load_baselines(sb, crop_type, pilot_district)


def _first_row(data: Any) -> dict[str, Any] | None:
    if data is None:
        return None
    if isinstance(data, list):
        return data[0] if data else None
    return data


def _fetch_boundary_geojson(sb, field_id: str) -> dict[str, Any]:
    try:
        resp = sb.rpc("field_boundary_geojson", {"p_field_id": field_id}).execute()
        if resp.data:
            return resp.data
    except Exception:
        pass
    return {"type": "Polygon", "coordinates": []}


def _boundary_from_row(sb, row: dict) -> dict[str, Any]:
    if isinstance(row.get("boundary"), dict):
        return row["boundary"]
    if row.get("boundary_geojson"):
        return row["boundary_geojson"]
    return _fetch_boundary_geojson(sb, row["id"])


def _field_response(sb, row: dict, risk_tier: str | None = None) -> FieldResponse:
    return FieldResponse(
        id=row["id"],
        institution_id=row["institution_id"],
        name=row.get("name"),
        boundary_geojson=_boundary_from_row(sb, row),
        area_hectares=float(row["area_hectares"]) if row.get("area_hectares") else None,
        crop_type=row["crop_type"],
        sowing_date=date.fromisoformat(str(row["sowing_date"])),
        farmer_ref_id=row.get("farmer_ref_id"),
        loan_ref_id=row.get("loan_ref_id"),
        status=row["status"],
        resolution_warning=row.get("resolution_warning", False),
        pilot_district=row.get("pilot_district", "matiari"),
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

    from app.services.tiers.gee_client import is_gee_configured

    if not is_gee_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Satellite analysis requires Google Earth Engine. "
                "Configure GEE_SERVICE_ACCOUNT_EMAIL and GEE_PRIVATE_KEY_PATH in backend/.env"
            ),
        )

    resolution_warning = validate_field_area(area, settings)
    sb = get_supabase_admin()

    resp = sb.rpc(
        "create_field_from_geojson",
        {
            "p_institution_id": institution_id,
            "p_created_by": user_id,
            "p_name": payload.name,
            "p_boundary": geojson,
            "p_area_hectares": round(area, 4),
            "p_crop_type": payload.crop_type,
            "p_sowing_date": payload.sowing_date.isoformat(),
            "p_farmer_ref_id": payload.farmer_ref_id,
            "p_loan_ref_id": payload.loan_ref_id,
            "p_resolution_warning": resolution_warning,
            "p_pilot_district": settings.pilot_district,
        },
    ).execute()
    row = _first_row(resp.data)
    if not row:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Field insert failed")
    process_field(row["id"], settings)
    return get_field(row["id"], institution_id)


def get_field(field_id: str, institution_id: str) -> FieldResponse:
    sb = get_supabase_admin()
    resp = sb.table("fields").select("*").eq("id", field_id).eq("institution_id", institution_id).single().execute()
    row = _first_row(resp.data)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")

    risk_resp = (
        sb.table("risk_assessments")
        .select("risk_tier")
        .eq("field_id", field_id)
        .eq("is_current", True)
        .limit(1)
        .execute()
    )
    risk_row = _first_row(risk_resp.data)
    risk_tier = risk_row["risk_tier"] if risk_row else None
    return _field_response(sb, row, risk_tier)


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

    return [_field_response(sb, r, risk_map.get(r["id"])) for r in resp.data]


def update_field(
    field_id: str,
    payload: FieldUpdateRequest,
    institution_id: str,
    settings: Settings,
) -> FieldResponse:
    sb = get_supabase_admin()
    existing = sb.table("fields").select("*").eq("id", field_id).eq("institution_id", institution_id).single().execute()
    if not _first_row(existing.data):
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
        resolution_warning = validate_field_area(area, settings)
        sb.rpc(
            "update_field_boundary",
            {
                "p_field_id": field_id,
                "p_boundary": geojson,
                "p_area_hectares": round(area, 4),
                "p_resolution_warning": resolution_warning,
            },
        ).execute()
        updates["_boundary_changed"] = True

    if updates:
        table_updates = {k: v for k, v in updates.items() if not k.startswith("_")}
        if table_updates:
            sb.table("fields").update(table_updates).eq("id", field_id).execute()
        if updates.get("_boundary_changed") or any(k in updates for k in ("sowing_date", "crop_type")):
            process_field(field_id, settings)

    return get_field(field_id, institution_id)


def get_field_detail(field_id: str, institution_id: str) -> dict:
    sb = get_supabase_admin()
    field_resp = sb.table("fields").select("*").eq("id", field_id).eq("institution_id", institution_id).single().execute()
    field_row = _first_row(field_resp.data)
    if not field_row:
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
        .eq("crop_type", field_row["crop_type"])
        .eq("pilot_district", field_row["pilot_district"])
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
    assessment_row = _first_row(assessment)
    if assessment_row and assessment_row.get("primary_data_tier") and baseline:
        tier = DataTier(assessment_row["primary_data_tier"])
        family = index_family_for_tier(tier.value)
        matched = [
            b for b in baseline
            if index_family_for_tier(str(b.get("primary_tier", "tier3_sar"))) == family
        ]
        if matched:
            baseline = matched
    risk_tier = assessment_row["risk_tier"] if assessment_row else None

    audit_resp = (
        sb.table("risk_audit_log")
        .select("payload")
        .eq("field_id", field_id)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    audit_row = _first_row(audit_resp.data)
    pipeline = audit_row.get("payload") if audit_row else None

    return {
        "field": _field_response(sb, field_row, risk_tier),
        "vegetation_readings": readings,
        "baseline": baseline,
        "current_assessment": assessment_row,
        "pipeline": pipeline,
    }


def process_field(field_id: str, settings: Settings) -> None:
    sb = get_supabase_admin()
    field = _first_row(sb.table("fields").select("*").eq("id", field_id).single().execute().data)
    if not field:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    sowing = date.fromisoformat(str(field["sowing_date"]))
    boundary = _boundary_from_row(sb, field)
    wkt = geojson_to_wkt(boundary)

    from app.services.tiers.gee_client import GEEError

    try:
        fused_result = select_and_fuse(wkt, sowing)
    except GEEError as exc:
        logger.error("Vegetation fusion failed for field %s: %s", field_id, exc)
        fused_result = FusionResult(
            readings=[],
            pipeline={
                "tier1": "empty",
                "tier2": "empty",
                "tier3": "gee_error",
                "vegetation_source": "gee_error",
                "reading_count": "0",
            },
        )

    fused = fused_result.readings
    pipeline_meta = fused_result.pipeline

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

    baseline_rows = _ensure_gee_baselines(
        sb, wkt, sowing, field["crop_type"], field["pilot_district"]
    )

    rainfall_mm = None
    rainfall_anomaly_pct = None
    rainfall_source = "none"
    from app.services.tiers.gee_client import fetch_chirps_rainfall, is_gee_configured

    if is_gee_configured():
        try:
            end = date.today()
            start = end.replace(day=1)
            ctx = fetch_chirps_rainfall(wkt, start, end)
            rainfall_mm = ctx.period_mm
            rainfall_anomaly_pct = ctx.anomaly_pct
            rainfall_source = "gee_chirps"
        except Exception:
            rainfall_source = "gee_error"

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

    audit_payload = {
        **result.audit_payload,
        **pipeline_meta,
        "rainfall_source": rainfall_source,
    }

    sb.table("risk_assessments").update({"is_current": False}).eq("field_id", field_id).execute()
    assessment_resp = sb.table("risk_assessments").insert({
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
    }).execute()
    assessment = _first_row(assessment_resp.data)
    if not assessment:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Risk assessment insert failed")

    sb.table("risk_audit_log").insert({
        "field_id": field_id,
        "risk_assessment_id": assessment["id"],
        "event_type": "risk_assessed",
        "payload": audit_payload,
    }).execute()
