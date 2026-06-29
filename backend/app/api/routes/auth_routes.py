from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthUser, get_current_user, require_admin
from app.core.config import get_settings
from app.core.supabase_client import get_supabase_admin
from app.schemas.domain import (
    InstitutionRegisterRequest,
    InstitutionResponse,
    InviteUserRequest,
    ProfileResponse,
    TeamMemberResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _auth_error_detail(exc: Exception) -> str:
    msg = getattr(exc, "message", None) or str(exc)
    if hasattr(exc, "msg") and exc.msg:
        msg = str(exc.msg)
    return msg


def _app_redirect_url() -> str:
    settings = get_settings()
    return settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:5173"


@router.post("/register-institution", response_model=InstitutionResponse)
async def register_institution(payload: InstitutionRegisterRequest):
    sb = get_supabase_admin()

    try:
        auth_resp = sb.auth.admin.create_user({
            "email": payload.admin_email,
            "password": payload.admin_password,
            "email_confirm": True,
        })
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_auth_error_detail(exc)) from exc

    user_id = auth_resp.user.id

    inst_resp = sb.rpc(
        "register_institution",
        {
            "p_name": payload.name,
            "p_contact_email": payload.contact_email,
            "p_admin_user_id": user_id,
            "p_admin_name": payload.admin_full_name,
            "p_contact_phone": payload.contact_phone,
        },
    ).execute()

    institution_id = inst_resp.data
    inst_rows = (
        sb.table("institutions")
        .select("*")
        .eq("id", institution_id)
        .limit(1)
        .execute()
        .data
    )
    inst = inst_rows[0] if inst_rows else None
    if not inst:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Institution insert failed")

    return InstitutionResponse(
        id=inst["id"],
        name=inst["name"],
        contact_email=inst["contact_email"],
        contact_phone=inst.get("contact_phone"),
    )


@router.get("/me", response_model=ProfileResponse)
async def get_me(user: AuthUser = Depends(get_current_user)):
    return ProfileResponse(
        id=user.id,
        institution_id=user.institution_id,
        role=user.role,
        full_name=user.full_name,
        email=user.email,
    )


@router.get("/team", response_model=list[TeamMemberResponse])
async def list_team(user: AuthUser = Depends(get_current_user)):
    sb = get_supabase_admin()
    rows = (
        sb.table("profiles")
        .select("id, role, full_name, created_at")
        .eq("institution_id", user.institution_id)
        .order("created_at")
        .execute()
        .data
        or []
    )
    return [
        TeamMemberResponse(
            id=r["id"],
            role=r["role"],
            full_name=r.get("full_name"),
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/invite")
async def invite_user(payload: InviteUserRequest, admin: AuthUser = Depends(require_admin)):
    sb = get_supabase_admin()
    redirect = f"{_app_redirect_url()}/login"

    try:
        auth_resp = sb.auth.admin.invite_user_by_email(
            payload.email,
            options={
                "redirect_to": redirect,
                "data": {"full_name": payload.full_name or ""},
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=_auth_error_detail(exc)) from exc

    user_id = auth_resp.user.id

    sb.table("profiles").insert({
        "id": user_id,
        "institution_id": admin.institution_id,
        "role": payload.role.value,
        "full_name": payload.full_name,
    }).execute()

    return {
        "message": f"Invitation email sent to {payload.email}. They can set a password from the link.",
        "user_id": user_id,
    }
