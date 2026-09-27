import logging

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.core.security import sanitize_health_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


def _detail_enabled(settings: Settings) -> bool:
    return settings.health_detail_enabled and not settings.is_production


@router.get("/supabase")
async def supabase_health(settings: Settings = Depends(get_settings)):
    """Check Supabase connectivity and required schema objects."""
    result = {
        "configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "connection": "unknown",
        "postgis_rpc": "unknown",
    }
    if _detail_enabled(settings):
        result["jwt_secret_configured"] = bool(settings.supabase_jwt_secret)

    if not result["configured"]:
        result["connection"] = "missing_credentials"
        return result

    try:
        from app.core.supabase_client import get_supabase_admin

        sb = get_supabase_admin()
        tiers = sb.table("tier_status").select("tier").execute()
        result["connection"] = "ok"
        if _detail_enabled(settings):
            result["tier_count"] = len(tiers.data)
    except Exception as exc:
        result["connection"] = sanitize_health_error(exc, settings)
        return result

    try:
        sb.rpc("field_boundary_geojson", {"p_field_id": "00000000-0000-0000-0000-000000000000"}).execute()
        result["postgis_rpc"] = "ok"
    except Exception as exc:
        msg = str(exc).lower()
        if "does not exist" in msg:
            result["postgis_rpc"] = "migration_002_required"
        else:
            result["postgis_rpc"] = sanitize_health_error(exc, settings)

    return result


@router.get("/sen2sr")
async def sen2sr_health():
    """Check Tier 2 (local SEN2SR model + GEE fallback)."""
    from app.services.tiers.gee_client import is_gee_configured
    from app.services.tiers.sen2sr_local import is_local_model_available

    settings = get_settings()
    local = is_local_model_available(settings)
    gee = is_gee_configured()
    pipeline = "sen2sr_local" if local else "gee_weekly_composite"
    return {
        "enabled": settings.sen2sr_enabled,
        "use_local": settings.sen2sr_use_local,
        "local_model_loaded": local,
        "gee_configured": gee,
        "available": settings.sen2sr_enabled and (local or gee),
        "pipeline": pipeline,
    }


@router.get("/ml")
async def ml_health():
    """Check M12 gradient-boosted risk model availability."""
    from app.services.ml_risk import is_ml_model_available

    settings = get_settings()
    loaded = is_ml_model_available(settings)
    return {
        "enabled": settings.ml_risk_enabled,
        "model_loaded": loaded,
        "available": settings.ml_risk_enabled and loaded,
        "elevate_only": settings.ml_risk_elevate_only,
        "confidence_min": settings.ml_risk_confidence_min,
        "model_type": "gradient_boosting",
    }


@router.get("/gee")
async def gee_health(settings: Settings = Depends(get_settings)):
    """Check Google Earth Engine Tier 3 configuration and connectivity."""
    from app.services.tiers.gee_client import gee_health_probe

    result = dict(gee_health_probe())
    if result.get("connection") == "error" and not _detail_enabled(settings):
        logger.warning("GEE health check error: %s", result.get("message"))
        result["message"] = "error"
    return result
