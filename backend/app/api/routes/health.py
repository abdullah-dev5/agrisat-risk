from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/supabase")
async def supabase_health():
    """Check Supabase connectivity and required schema objects."""
    settings = get_settings()
    result = {
        "configured": bool(settings.supabase_url and settings.supabase_service_role_key),
        "jwt_secret_configured": bool(settings.supabase_jwt_secret),
        "connection": "unknown",
        "postgis_rpc": "unknown",
        "tier_count": 0,
    }

    if not result["configured"]:
        result["connection"] = "missing_credentials"
        return result

    try:
        from app.core.supabase_client import get_supabase_admin

        sb = get_supabase_admin()
        tiers = sb.table("tier_status").select("tier").execute()
        result["connection"] = "ok"
        result["tier_count"] = len(tiers.data)
    except Exception as exc:
        result["connection"] = f"error: {exc}"
        return result

    try:
        sb.rpc("field_boundary_geojson", {"p_field_id": "00000000-0000-0000-0000-000000000000"}).execute()
        result["postgis_rpc"] = "ok"
    except Exception as exc:
        msg = str(exc).lower()
        if "does not exist" in msg:
            result["postgis_rpc"] = "migration_002_required"
        else:
            result["postgis_rpc"] = "ok"

    return result
