from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import DataTier, FieldStatus, RiskTier, UserRole


class InstitutionRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    contact_email: EmailStr
    contact_phone: str | None = None
    admin_full_name: str | None = None
    admin_email: EmailStr
    admin_password: str = Field(min_length=8)


class InstitutionResponse(BaseModel):
    id: str
    name: str
    contact_email: str
    contact_phone: str | None = None


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role: UserRole = UserRole.LOAN_OFFICER


class ProfileResponse(BaseModel):
    id: str
    institution_id: str
    role: UserRole
    full_name: str | None = None
    email: str | None = None


class TeamMemberResponse(BaseModel):
    id: str
    role: UserRole
    full_name: str | None = None
    created_at: datetime


class FieldCreateRequest(BaseModel):
    name: str | None = None
    boundary_geojson: dict[str, Any]
    crop_type: str = "wheat"
    sowing_date: date
    farmer_ref_id: str | None = None
    loan_ref_id: str | None = None


class FieldUpdateRequest(BaseModel):
    name: str | None = None
    boundary_geojson: dict[str, Any] | None = None
    crop_type: str | None = None
    sowing_date: date | None = None
    farmer_ref_id: str | None = None
    loan_ref_id: str | None = None
    status: FieldStatus | None = None


class FieldResponse(BaseModel):
    id: str
    institution_id: str
    name: str | None = None
    boundary_geojson: dict[str, Any]
    area_hectares: float | None = None
    crop_type: str
    sowing_date: date
    farmer_ref_id: str | None = None
    loan_ref_id: str | None = None
    status: FieldStatus
    resolution_warning: bool
    pilot_district: str
    current_risk_tier: RiskTier | None = None
    processing_status: str | None = None
    processing_error: str | None = None
    created_at: datetime


class FieldProcessingStatusResponse(BaseModel):
    field_id: str
    status: str
    error: str | None = None
    updated_at: datetime | None = None


class VegetationReadingResponse(BaseModel):
    acquisition_date: date
    days_since_sowing: int
    data_tier: DataTier
    ndvi: float | None = None
    evi: float | None = None
    sar_index: float | None = None
    cloud_fraction: float | None = None
    is_fused: bool


class BaselinePointResponse(BaseModel):
    days_since_sowing: int
    mean_index: float
    std_index: float


class RiskAssessmentResponse(BaseModel):
    id: str
    field_id: str
    assessed_at: datetime
    days_since_sowing: int
    z_score: float | None = None
    risk_tier: RiskTier
    primary_data_tier: DataTier | None = None
    index_value: float | None = None
    baseline_mean: float | None = None
    baseline_std: float | None = None
    rainfall_mm: float | None = None
    rainfall_anomaly_pct: float | None = None
    explanation: str


class ImageryLayerResponse(BaseModel):
    thumb_url: str
    tiles: dict[str, str] | None = None


class ImagerySceneResponse(BaseModel):
    date: str
    cloud_pct: float
    ndvi_mean: float | None = None
    rgb: ImageryLayerResponse
    ndvi: ImageryLayerResponse


class FieldImageryResponse(BaseModel):
    source: str
    latest: ImagerySceneResponse
    compare: ImagerySceneResponse | None = None
    ndvi_delta: float | None = None
    tile_url_template: str | None = None


class FieldDetailResponse(FieldResponse):
    vegetation_readings: list[VegetationReadingResponse] = []
    baseline: list[BaselinePointResponse] = []
    current_assessment: RiskAssessmentResponse | None = None
    pipeline: dict | None = None


class PortfolioSummaryResponse(BaseModel):
    total_fields: int
    risk_counts: dict[str, int]
    flagged_fields: list[FieldResponse]
