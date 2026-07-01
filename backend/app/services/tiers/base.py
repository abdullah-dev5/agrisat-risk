"""Tier adapters — Sentinel-1/2, SEN2SR, Planet (live data only)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
import logging

logger = logging.getLogger(__name__)


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


@dataclass
class TierFetchResult:
    readings: list[TierReading]
    source: str  # gee_live | sen2sr | planet | empty | gee_error


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

    def fetch_with_meta(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> TierFetchResult:
        readings = self.fetch_readings(boundary_wkt, sowing_date, season_end)
        return TierFetchResult(readings=readings, source="unknown")


class Tier3Adapter(TierAdapter):
    """GEE-backed Sentinel-1/2 — required for vegetation analysis."""

    @property
    def tier_name(self) -> str:
        return "tier3_sar"

    def is_available(self) -> bool:
        from app.services.tiers.gee_client import is_gee_configured

        return is_gee_configured()

    def fetch_with_meta(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> TierFetchResult:
        from app.services.tiers.gee_client import GEEError, fetch_tier3_from_gee, is_gee_configured

        if not is_gee_configured():
            raise GEEError(
                "Google Earth Engine is not configured. "
                "Set GEE_SERVICE_ACCOUNT_EMAIL and GEE_PRIVATE_KEY_PATH in backend/.env"
            )

        readings = fetch_tier3_from_gee(boundary_wkt, sowing_date, season_end)
        logger.info("Tier 3: fetched %d GEE readings", len(readings))
        return TierFetchResult(readings=readings, source="gee_live")

    def fetch_readings(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> list[TierReading]:
        return self.fetch_with_meta(boundary_wkt, sowing_date, season_end).readings


class Tier2Adapter(TierAdapter):
    @property
    def tier_name(self) -> str:
        return "tier2_sen2sr"

    def is_available(self) -> bool:
        from app.core.config import get_settings

        return get_settings().sen2sr_enabled

    def fetch_with_meta(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> TierFetchResult:
        if not self.is_available():
            return TierFetchResult(readings=[], source="empty")

        try:
            from app.services.tiers.sen2sr import fetch_tier2_readings
            from app.services.tiers.sen2sr_local import is_local_model_available

            readings = fetch_tier2_readings(boundary_wkt, sowing_date, season_end)
            if readings and is_local_model_available():
                source = "sen2sr_local"
            elif readings:
                source = "sen2sr_gee"
            else:
                source = "empty"
            return TierFetchResult(readings=readings, source=source)
        except Exception as exc:
            logger.warning("Tier 2 SEN2SR unavailable: %s", exc)
            return TierFetchResult(readings=[], source="empty")

    def fetch_readings(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> list[TierReading]:
        return self.fetch_with_meta(boundary_wkt, sowing_date, season_end).readings


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
