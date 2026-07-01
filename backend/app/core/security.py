"""Production security helpers."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

_rate_lock = Lock()
_rate_buckets: dict[str, list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(
    request: Request,
    *,
    scope: str,
    max_calls: int,
    window_seconds: int,
) -> None:
    settings = get_settings()
    if settings.app_env != "production":
        return

    key = f"{scope}:{client_ip(request)}"
    now = time.time()
    with _rate_lock:
        bucket = [t for t in _rate_buckets[key] if now - t < window_seconds]
        if len(bucket) >= max_calls:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
        bucket.append(now)
        _rate_buckets[key] = bucket


def verify_registration_allowed(request: Request, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    check_rate_limit(request, scope="register", max_calls=5, window_seconds=3600)

    if settings.allow_open_registration:
        return

    secret = request.headers.get("x-registration-secret", "")
    if not settings.registration_secret or secret != settings.registration_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Institution registration is disabled. Contact the platform administrator.",
        )


def public_error_message(exc: Exception, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if settings.app_env == "production":
        return "An internal error occurred. Please try again or contact support."
    return str(exc)


def sanitize_health_error(exc: Exception, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    if settings.health_detail_enabled:
        return str(exc)
    logger.warning("Health check error: %s", exc)
    return "error"
