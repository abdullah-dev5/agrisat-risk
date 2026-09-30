"""Regression test for clock-skew tolerance in JWT verification.

Discovered via a live E2E run: this dev machine's clock was ~24s behind the
real Supabase auth server's clock, and a freshly-issued (genuinely valid)
token was rejected with jwt.exceptions.ImmatureSignatureError, because
verify_supabase_token's JWKS/PyJWT branch had zero leeway on the `iat`
claim -- meaning ANY deployment with even minor clock drift (VM clock skew,
a missed NTP sync) would reject every single login, not just malformed or
genuinely-expired tokens. Fixed by adding a 30s leeway to both branches.

Two things are tested separately, for a concrete reason:
- The PyJWT (JWKS/ES256) branch is what this deployment actually uses
  (SUPABASE_JWT_SECRET is unset -- see docs/ARCHITECTURE.md). PyJWT is the
  library that raised ImmatureSignatureError on `iat`, so its leeway
  behavior is tested directly against PyJWT (HS256 here, same leeway
  mechanics as the ES256 path actually used in production -- avoids needing
  a live JWKS endpoint just to prove the leeway kwarg works).
- The legacy python-jose (HS256 shared-secret) branch is tested through
  verify_supabase_token itself, since it's simple to exercise without any
  network call (supabase_url="" skips the JWKS attempt entirely). Notably,
  python-jose's `_validate_iat` never checks whether `iat` is in the future
  at all (only that it's an int) -- unlike PyJWT, it wouldn't have hit this
  bug in the first place. Its leeway option still matters for `exp`/`nbf`,
  which is what's tested here.
"""
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt

from app.core.config import Settings
from app.core.jwt_verify import verify_supabase_token

SECRET = "test-only-hs256-secret-not-a-real-credential"


# --- PyJWT leeway mechanics (the library actually used by the JWKS/ES256
# branch that hit the real bug) ---


def test_pyjwt_leeway_tolerates_a_token_issued_slightly_in_the_future():
    now = datetime.now(timezone.utc)
    token = pyjwt.encode(
        {"sub": "user-123", "aud": "authenticated", "iat": now + timedelta(seconds=20), "exp": now + timedelta(hours=1)},
        SECRET,
        algorithm="HS256",
    )
    claims = pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="authenticated", leeway=30)
    assert claims["sub"] == "user-123"


def test_pyjwt_without_leeway_rejects_the_same_token():
    # Proves the leeway kwarg is actually load-bearing, not a no-op.
    now = datetime.now(timezone.utc)
    token = pyjwt.encode(
        {"sub": "user-123", "aud": "authenticated", "iat": now + timedelta(seconds=20), "exp": now + timedelta(hours=1)},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(pyjwt.exceptions.ImmatureSignatureError):
        pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="authenticated", leeway=0)


def test_pyjwt_leeway_does_not_tolerate_a_token_issued_far_in_the_future():
    # 30s leeway should absorb clock drift, not a token that's genuinely not
    # valid yet -- 10 minutes ahead should still fail.
    now = datetime.now(timezone.utc)
    token = pyjwt.encode(
        {"sub": "user-123", "aud": "authenticated", "iat": now + timedelta(minutes=10), "exp": now + timedelta(hours=1)},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(pyjwt.exceptions.ImmatureSignatureError):
        pyjwt.decode(token, SECRET, algorithms=["HS256"], audience="authenticated", leeway=30)


# --- verify_supabase_token via the legacy python-jose (HS256 shared-secret)
# branch -- supabase_url="" skips the JWKS attempt, no network call needed.


def _make_legacy_token(iat_offset_seconds: int, exp_offset_seconds: int = 3600) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "user-123",
        "aud": "authenticated",
        "iat": now + timedelta(seconds=iat_offset_seconds),
        "exp": now + timedelta(seconds=exp_offset_seconds),
    }
    return jose_jwt.encode(payload, SECRET, algorithm="HS256")


def _legacy_settings() -> Settings:
    return Settings(supabase_url="", supabase_jwt_secret=SECRET)


def test_legacy_path_accepts_a_token_issued_slightly_in_the_future():
    token = _make_legacy_token(iat_offset_seconds=20)
    claims = verify_supabase_token(token, _legacy_settings())
    assert claims["sub"] == "user-123"


def test_legacy_path_rejects_an_expired_token_even_with_leeway():
    token = _make_legacy_token(iat_offset_seconds=-7200, exp_offset_seconds=-3600)
    with pytest.raises(HTTPException) as exc_info:
        verify_supabase_token(token, _legacy_settings())
    assert exc_info.value.status_code == 401
