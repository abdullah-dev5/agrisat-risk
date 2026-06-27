"""Tier 3 — Sentinel-1 SAR + Sentinel-2 + CHIRPS (always-available baseline)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class TierReading:
    acquisition_date: date
    ndvi: float | None = None
    evi: float | None = None
    sar_index: float | None = None
    cloud_fraction: float | None = None


@dataclass
class RainfallContext:
    period_mm: float
    historical_mean_mm: float
    anomaly_pct: float


class TierAdapter(ABC):
    @property
    @abstractmethod
    def tier_name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        pass

    @abstractmethod
    def fetch_readings(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> list[TierReading]:
        pass


class Tier3Adapter(TierAdapter):
    """GEE-backed Sentinel-1/2 + CHIRPS. Falls back to demo data when GEE is not configured."""

    @property
    def tier_name(self) -> str:
        return "tier3_sar"

    def is_available(self) -> bool:
        return True

    def fetch_readings(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> list[TierReading]:
        try:
            from app.services.tiers.gee_client import fetch_tier3_from_gee

            return fetch_tier3_from_gee(boundary_wkt, sowing_date, season_end)
        except Exception:
            from app.services.tiers.demo_data import generate_demo_readings

            return generate_demo_readings(sowing_date, tier="tier3_sar")


class Tier2Adapter(TierAdapter):
    @property
    def tier_name(self) -> str:
        return "tier2_sen2sr"

    def is_available(self) -> bool:
        from app.core.config import get_settings

        return get_settings().sen2sr_enabled

    def fetch_readings(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> list[TierReading]:
        # SEN2SR pipeline placeholder — uses enhanced S2 when model runtime is configured
        try:
            from app.services.tiers.sen2sr import fetch_tier2_readings

            return fetch_tier2_readings(boundary_wkt, sowing_date, season_end)
        except Exception:
            from app.services.tiers.demo_data import generate_demo_readings

            return generate_demo_readings(sowing_date, tier="tier2_sen2sr")


class Tier1Adapter(TierAdapter):
    @property
    def tier_name(self) -> str:
        return "tier1_planet"

    def is_available(self) -> bool:
        from app.core.config import get_settings

        return bool(get_settings().planet_api_key)

    def fetch_readings(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> list[TierReading]:
        if not self.is_available():
            return []
        try:
            from app.services.tiers.planet import fetch_tier1_readings

            return fetch_tier1_readings(boundary_wkt, sowing_date, season_end)
        except Exception:
            return []
