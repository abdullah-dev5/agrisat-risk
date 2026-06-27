from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    gee_service_account_email: str = ""
    gee_private_key_path: str = ""

    planet_api_key: str = ""
    sen2sr_model_path: str = "./models/sen2sr"
    sen2sr_enabled: bool = True

    pilot_crop: str = "wheat"
    pilot_district: str = "faisalabad"
    pilot_region_bbox: str = "72.0,30.8,73.5,31.8"

    risk_threshold_watch: float = 1.0
    risk_threshold_elevated: float = 1.5
    risk_threshold_high: float = 2.0

    min_field_hectares: float = 0.2
    max_field_hectares: float = 500.0

    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
