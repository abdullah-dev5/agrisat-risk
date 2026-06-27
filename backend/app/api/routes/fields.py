from fastapi import APIRouter, Depends, Query

from app.core.auth import AuthUser, get_current_user
from app.core.config import Settings, get_settings
from app.schemas.domain import FieldCreateRequest, FieldDetailResponse, FieldResponse, FieldUpdateRequest
from app.services import field_service

router = APIRouter(prefix="/fields", tags=["fields"])


@router.get("", response_model=list[FieldResponse])
async def list_fields(
    status: str | None = Query(default="active"),
    user: AuthUser = Depends(get_current_user),
):
    return field_service.list_fields(user.institution_id, status)


@router.post("", response_model=FieldResponse)
async def create_field(
    payload: FieldCreateRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    return field_service.create_field(payload, user.institution_id, user.id, settings)


@router.get("/{field_id}", response_model=FieldResponse)
async def get_field(field_id: str, user: AuthUser = Depends(get_current_user)):
    return field_service.get_field(field_id, user.institution_id)


@router.get("/{field_id}/detail", response_model=FieldDetailResponse)
async def get_field_detail(field_id: str, user: AuthUser = Depends(get_current_user)):
    detail = field_service.get_field_detail(field_id, user.institution_id)
    field = detail["field"]
    assessment = detail.get("current_assessment")
    return FieldDetailResponse(
        **field.model_dump(),
        vegetation_readings=detail["vegetation_readings"],
        baseline=detail["baseline"],
        current_assessment=assessment,
    )


@router.patch("/{field_id}", response_model=FieldResponse)
async def update_field(
    field_id: str,
    payload: FieldUpdateRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    return field_service.update_field(field_id, payload, user.institution_id, settings)


@router.post("/{field_id}/reprocess")
async def reprocess_field(
    field_id: str,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    field_service.get_field(field_id, user.institution_id)
    field_service.process_field(field_id, settings)
    return {"message": "Field reprocessed successfully"}
