"""Background field processing — keeps HTTP handlers fast (production)."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from app.core.config import Settings, get_settings
from app.core.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agrisat-gee")
_active: set[str] = set()
_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def set_processing_status(
    field_id: str,
    status: str,
    error: str | None = None,
) -> None:
    sb = get_supabase_admin()
    payload: dict = {
        "processing_status": status,
        "processing_updated_at": _utc_now(),
    }
    if error is not None:
        payload["processing_error"] = error[:500]
    elif status in ("ready", "idle", "processing"):
        payload["processing_error"] = None
    sb.table("fields").update(payload).eq("id", field_id).execute()


def is_field_processing(field_id: str) -> bool:
    with _lock:
        return field_id in _active


def enqueue_field_processing(field_id: str, settings: Settings | None = None) -> bool:
    """Schedule GEE fusion + risk scoring. Returns False if already running."""
    settings = settings or get_settings()

    with _lock:
        if field_id in _active:
            logger.info("Field %s already processing — skip duplicate job", field_id)
            return False
        _active.add(field_id)

    set_processing_status(field_id, "processing")

    def _run() -> None:
        try:
            from app.services.field_service import process_field

            process_field(field_id, settings)
            set_processing_status(field_id, "ready")
        except Exception as exc:
            logger.exception("Field processing failed for %s", field_id)
            set_processing_status(field_id, "failed", str(exc))
        finally:
            with _lock:
                _active.discard(field_id)

    _executor.submit(_run)
    return True


def shutdown_executor() -> None:
    _executor.shutdown(wait=False, cancel_futures=True)
