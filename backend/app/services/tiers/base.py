"""Tier adapters — Sentinel-1/2, SEN2SR, Planet."""

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
    source: str  # gee_live | demo_fallback | sen2sr | planet | empty


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
    """GEE-backed Sentinel-1/2 + CHIRPS. Falls back to demo data when GEE is not configured."""

    @property
    def tier_name(self) -> str:
        return "tier3_sar"

    def is_available(self) -> bool:
        return True

    def fetch_with_meta(
        self,
        boundary_wkt: str,
        sowing_date: date,
        season_end: date | None = None,
    ) -> TierFetchResult:
        from app.core.config import get_settings
        from app.services.tiers.gee_client import is_gee_configured

        settings = get_settings()
        if not is_gee_configured():
            from app.services.tiers.demo_data import generate_demo_readings

            logger.warning("Tier 3: GEE not configured — using demo vegetation readings")
            return TierFetchResult(
                readings=generate_demo_readings(sowing_date, tier="tier3_sar"),
                source="demo_fallback",
            )

        try:
            from app.services.tiers.gee_client import fetch_tier3_from_gee

            readings = fetch_tier3_from_gee(boundary_wkt, sowing_date, season_end)
            logger.info("Tier 3: fetched %d GEE readings", len(readings))
            return TierFetchResult(readings=readings, source="gee_live")
        except Exception as exc:
            if settings.gee_allow_demo_fallback:
                from app.services.tiers.demo_data import generate_demo_readings

                logger.warning("Tier 3 GEE failed (%s) — demo fallback enabled", exc)
                return TierFetchResult(
                    readings=generate_demo_readings(sowing_date, tier="tier3_sar"),
                    source="demo_fallback",
                )
            raise

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
        try:
            from app.services.tiers.sen2sr import fetch_tier2_readings

            return TierFetchResult(
                readings=fetch_tier2_readings(boundary_wkt, sowing_date, season_end),
                source="sen2sr",
            )
        except Exception:
            from app.services.tiers.demo_data import generate_demo_readings

            return TierFetchResult(
                readings=generate_demo_readings(sowing_date, tier="tier2_sen2sr"),
                source="demo_fallback",
            )

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
