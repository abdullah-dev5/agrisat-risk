"""Verify Supabase access tokens (ES256 JWKS or legacy HS256 secret)."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from fastapi import HTTPException, status
from jose import JWTError, jwt as jose_jwt

from app.core.config import Settings


@lru_cache
def _jwks_client(supabase_url: str):
    from jwt import PyJWKClient

    url = supabase_url.rstrip("/")
    return PyJWKClient(f"{url}/auth/v1/.well-known/jwks.json", cache_keys=True)


def verify_supabase_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and validate a Supabase Auth JWT."""
    audience = "authenticated"
    # Tolerate minor clock drift between this server and Supabase's auth
    # server (NTP hiccups, VM clock skew) -- without this, a token whose
    # `iat` is even a few seconds "in the future" from this machine's clock
    # is rejected outright (jwt.exceptions.ImmatureSignatureError), which
    # would reject *every* fresh login on a machine with any clock drift,
    # not just malformed/expired tokens. 30s matches common practice (e.g.
    # Supabase's own client libraries default to similar tolerances).
    leeway_seconds = 30
    jwks_error: Exception | None = None

    if settings.supabase_url:
        try:
            from jwt import PyJWTError, decode as pyjwt_decode

            client = _jwks_client(settings.supabase_url)
            signing_key = client.get_signing_key_from_jwt(token)
            return pyjwt_decode(
                token,
                signing_key.key,
                algorithms=["ES256", "RS256"],
                audience=audience,
                leeway=leeway_seconds,
            )
        except Exception as exc:
            jwks_error = exc
            if not settings.supabase_jwt_secret:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if settings.supabase_jwt_secret:
        try:
            return jose_jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=audience,
                options={"leeway": leeway_seconds},
            )
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc

    if jwks_error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from jwks_error

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Auth not configured: set SUPABASE_URL (JWKS) or SUPABASE_JWT_SECRET (legacy)",
    )
