"""Background field processing — keeps HTTP handlers fast (production)."""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app.core.config import Settings, get_settings
from app.core.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="agrisat-gee")
_active: set[str] = set()
_lock = threading.Lock()
_reconcile_stop = threading.Event()
_reconcile_thread: threading.Thread | None = None


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


def enqueue_field_processing(
    field_id: str, institution_id: str, settings: Settings | None = None
) -> bool:
    """Schedule GEE fusion + risk scoring. Returns False if already running.

    Requires institution_id so process_field can verify ownership itself
    (docs/AUDIT-FINDINGS.md #13) — every current caller already validates
    ownership before enqueuing, but this closes the gap for any future caller
    that doesn't, rather than relying solely on caller discipline.
    """
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

            process_field(field_id, institution_id, settings)
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


def reconcile_stale_processing(timeout_minutes: int) -> int:
    """Reset fields stuck in 'processing' past a timeout.

    A crashed or killed worker process leaves a field's `processing_status`
    row at "processing" forever, since nothing else ever updates it — the
    in-memory `_active` set that would normally clear it dies with the
    process. This sweep finds rows stale enough to be implausible for a
    still-running job (excluding anything this same process currently has in
    `_active`, since that's a legitimately running job, just a slow one) and
    marks them "failed" so the UI stops showing "analysis in progress"
    indefinitely and the user can retry via reprocess.
    """
    sb = get_supabase_admin()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)).isoformat()
    resp = (
        sb.table("fields")
        .select("id")
        .eq("processing_status", "processing")
        .lt("processing_updated_at", cutoff)
        .execute()
    )
    with _lock:
        stale_ids = [row["id"] for row in resp.data if row["id"] not in _active]

    for field_id in stale_ids:
        set_processing_status(
            field_id,
            "failed",
            "Processing timed out or the worker crashed before completion. Use Re-analyze field to retry.",
        )

    if stale_ids:
        logger.warning("Reconciled %d stale processing field(s): %s", len(stale_ids), stale_ids)
    return len(stale_ids)


def _reconcile_loop(stop_event: threading.Event, settings: Settings) -> None:
    try:
        reconcile_stale_processing(settings.job_stale_timeout_minutes)
    except Exception:
        logger.exception("Initial processing-status reconciliation failed")

    while not stop_event.wait(settings.job_reconcile_interval_seconds):
        try:
            reconcile_stale_processing(settings.job_stale_timeout_minutes)
        except Exception:
            logger.exception("Processing-status reconciliation sweep failed")


def start_reconciliation_loop(settings: Settings | None = None) -> None:
    """Start the background sweep (idempotent — safe to call once at app startup)."""
    global _reconcile_thread
    if _reconcile_thread is not None and _reconcile_thread.is_alive():
        return
    settings = settings or get_settings()
    _reconcile_stop.clear()
    _reconcile_thread = threading.Thread(
        target=_reconcile_loop,
        args=(_reconcile_stop, settings),
        daemon=True,
        name="agrisat-reconcile",
    )
    _reconcile_thread.start()


def stop_reconciliation_loop() -> None:
    _reconcile_stop.set()
