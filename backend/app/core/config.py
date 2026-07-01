from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    gee_service_account_email: str = ""
    gee_private_key_path: str = ""
    gee_project: str = ""

    planet_api_key: str = ""
    sen2sr_model_path: str = "./models/sen2sr"
    sen2sr_enabled: bool = True
    sen2sr_use_local: bool = True

    ml_risk_enabled: bool = True
    ml_risk_model_path: str = "./models/ml_risk"
    ml_risk_elevate_only: bool = True
    ml_risk_confidence_min: float = 0.55

    app_env: str = "development"
    allow_open_registration: bool = True
    registration_secret: str = ""
    health_detail_enabled: bool = True
    trusted_hosts: str = ""
    baseline_build_on_request: bool = False

    pilot_crop: str = "wheat"
    pilot_district: str = "matiari"
    pilot_region_bbox: str = "68.0,25.2,69.2,26.1"

    risk_threshold_watch: float = 1.0
    risk_threshold_elevated: float = 1.5
    risk_threshold_high: float = 2.0

    min_field_hectares: float = 0.2
    max_field_hectares: float = 500.0

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def trusted_host_list(self) -> list[str]:
        return [h.strip() for h in self.trusted_hosts.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def resolved_gee_key_path(self) -> str:
        if not self.gee_private_key_path:
            return ""
        path = Path(self.gee_private_key_path)
        if path.is_absolute():
            return str(path)
        return str((BACKEND_ROOT / path).resolve())


@lru_cache
def get_settings() -> Settings:
    return Settings()
