"""Shared vegetation index transforms (GEE pipeline)."""

from __future__ import annotations


def sar_index_from_vv_db(vv_db: float) -> float:
    """Map Sentinel-1 VV backscatter (dB) to a 0–1 index comparable across pipeline stages."""
    return round(max(0.0, min(1.0, (vv_db + 22.0) / 18.0)), 5)


def index_family_for_tier(tier_value: str) -> str:
    return "sar" if tier_value == "tier3_sar" else "optical"


def effective_std(mean: float, std: float) -> float:
    """Avoid absurd z-scores when historical spread is near zero."""
    return max(std, abs(mean) * 0.08, 0.015)
