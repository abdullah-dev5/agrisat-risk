from fastapi import APIRouter, Depends, HTTPException, status

from app.core.auth import AuthUser, get_current_user, require_admin
from app.core.supabase_client import get_supabase_admin
from app.schemas.domain import InstitutionRegisterRequest, InstitutionResponse, InviteUserRequest, ProfileResponse

router = APIRouter(prefix="/auth", tags=["auth"])


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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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
    inst = sb.table("institutions").select("*").eq("id", institution_id).single().execute().data

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


@router.post("/invite")
async def invite_user(payload: InviteUserRequest, admin: AuthUser = Depends(require_admin)):
    sb = get_supabase_admin()
    try:
        auth_resp = sb.auth.admin.create_user({
            "email": payload.email,
            "email_confirm": True,
        })
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sb.table("profiles").insert({
        "id": auth_resp.user.id,
        "institution_id": admin.institution_id,
        "role": payload.role.value,
        "full_name": payload.full_name,
    }).execute()

    return {"message": f"Invited {payload.email}. User must reset password via Supabase invite flow."}
