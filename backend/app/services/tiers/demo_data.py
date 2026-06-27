"""Demo vegetation readings for development without GEE credentials."""

from datetime import date, timedelta
import math
import random

from app.services.tiers.base import TierReading


def generate_demo_readings(sowing_date: date, tier: str) -> list[TierReading]:
    random.seed(hash((sowing_date.isoformat(), tier)) % 2**32)
    readings: list[TierReading] = []
    today = date.today()
    day = 0
    while sowing_date + timedelta(days=day) <= today and day <= 120:
        acq = sowing_date + timedelta(days=day)
        progress = day / 120
        seasonal = 0.25 + 0.55 * math.sin(math.pi * progress)
        noise = random.uniform(-0.08, 0.08)
        ndvi = max(0.1, min(0.9, seasonal + noise))

        if tier == "tier3_sar":
            sar = 0.15 + ndvi * 0.2 + random.uniform(-0.02, 0.02)
            readings.append(
                TierReading(acquisition_date=acq, sar_index=round(sar, 5), cloud_fraction=0.0)
            )
        else:
            readings.append(
                TierReading(
                    acquisition_date=acq,
                    ndvi=round(ndvi, 5),
                    evi=round(ndvi * 1.05, 5),
                    cloud_fraction=round(random.uniform(0, 0.3), 3),
                )
            )
        day += 5
    return readings
