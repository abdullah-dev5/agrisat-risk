import logging

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import JSONResponse

from app.core.auth import AuthUser, get_current_user
from app.core.config import Settings, get_settings
from app.schemas.domain import (
    FieldCreateRequest,
    FieldDetailResponse,
    FieldImageryResponse,
    FieldProcessingStatusResponse,
    FieldResponse,
    FieldUpdateRequest,
    RiskAssessmentResponse,
)
from app.services import field_service

router = APIRouter(prefix="/fields", tags=["fields"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[FieldResponse])
def list_fields(
    status: str | None = Query(default="active"),
    user: AuthUser = Depends(get_current_user),
):
    return field_service.list_fields(user.institution_id, status)


@router.post("", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(
    payload: FieldCreateRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    """Create field boundary and enqueue GEE analysis (returns in <2s)."""
    return field_service.create_field(payload, user.institution_id, user.id, settings)


@router.get("/{field_id}", response_model=FieldResponse)
def get_field(field_id: str, user: AuthUser = Depends(get_current_user)):
    return field_service.get_field(field_id, user.institution_id)


@router.get("/{field_id}/processing", response_model=FieldProcessingStatusResponse)
def get_field_processing(field_id: str, user: AuthUser = Depends(get_current_user)):
    return field_service.get_processing_status(field_id, user.institution_id)


@router.get("/{field_id}/detail", response_model=FieldDetailResponse)
def get_field_detail(field_id: str, user: AuthUser = Depends(get_current_user)):
    detail = field_service.get_field_detail(field_id, user.institution_id)
    field = detail["field"]
    assessment_raw = detail.get("current_assessment")
    assessment = (
        RiskAssessmentResponse.model_validate(assessment_raw) if assessment_raw else None
    )
    return FieldDetailResponse(
        **field.model_dump(),
        vegetation_readings=detail["vegetation_readings"],
        baseline=detail["baseline"],
        current_assessment=assessment,
        pipeline=detail.get("pipeline"),
    )


@router.patch("/{field_id}", response_model=FieldResponse)
def update_field(
    field_id: str,
    payload: FieldUpdateRequest,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    return field_service.update_field(field_id, payload, user.institution_id, settings)


@router.get("/{field_id}/imagery", response_model=FieldImageryResponse)
def get_field_imagery(field_id: str, user: AuthUser = Depends(get_current_user)):
    return field_service.get_field_imagery(field_id, user.institution_id)


@router.post("/{field_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
def reprocess_field(
    field_id: str,
    user: AuthUser = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
):
    result = field_service.request_reprocess(field_id, user.institution_id, settings)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=result)
