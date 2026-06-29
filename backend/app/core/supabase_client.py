"""Supabase admin client — supports legacy JWT keys and new sb_secret_* opaque keys."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from app.core.config import get_settings

_OPAQUE_KEY_PREFIXES = ("sb_secret_", "sb_publishable_")


class _OpaqueAuth:
    """GoTrue admin API for opaque Supabase keys (sb_secret_*)."""

    def __init__(self, base_url: str, api_key: str) -> None:
        from gotrue import SyncGoTrueAdminAPI

        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
        }
        self.admin = SyncGoTrueAdminAPI(
            url=f"{base_url.rstrip('/')}/auth/v1",
            headers=headers,
        )


class _OpaqueAdminClient:
    """PostgREST + Auth admin client for Supabase opaque API keys."""

    def __init__(self, base_url: str, api_key: str) -> None:
        from postgrest import SyncPostgrestClient

        headers = {
            "apikey": api_key,
            "Authorization": f"Bearer {api_key}",
        }
        self._rest = SyncPostgrestClient(
            f"{base_url.rstrip('/')}/rest/v1",
            headers=headers,
        )
        self.auth = _OpaqueAuth(base_url, api_key)

    def table(self, name: str) -> Any:
        return self._rest.from_(name)

    def rpc(self, fn: str, params: dict[str, Any] | None = None) -> Any:
        return self._rest.rpc(fn, params or {})


def _is_opaque_key(key: str) -> bool:
    return key.startswith(_OPAQUE_KEY_PREFIXES)


@lru_cache
def get_supabase_admin() -> Any:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")

    key = settings.supabase_service_role_key
    if _is_opaque_key(key):
        return _OpaqueAdminClient(settings.supabase_url, key)

    from supabase import create_client

    return create_client(settings.supabase_url, key)
