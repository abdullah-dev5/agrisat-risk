"""Unit tests for the stale-processing reconciliation sweep (docs/AUDIT-FINDINGS.md #2).

Uses a hand-rolled fake Supabase client rather than the real one -- there's no
live Supabase in CI, and the query-builder chain (select/eq/lt/execute,
update/eq/execute) is simple enough to fake precisely and verify exact calls.
"""
from app.services import job_runner


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def lt(self, *_a, **_k):
        return self

    def execute(self):
        return _FakeResp(self._rows)


class _FakeTable:
    def __init__(self, rows, updates):
        self._rows = rows
        self._updates = updates
        self._pending_payload = None

    def select(self, *_a, **_k):
        return _FakeQuery(self._rows)

    def update(self, payload):
        self._pending_payload = payload
        return self

    def eq(self, field, value):
        if self._pending_payload is not None and field == "id":
            self._updates.append((value, self._pending_payload))
        return self

    def execute(self):
        return _FakeResp([])


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows
        self.updates: list[tuple[str, dict]] = []

    def table(self, _name):
        return _FakeTable(self.rows, self.updates)


def test_reconcile_marks_stale_fields_failed_and_skips_active_ones(monkeypatch):
    rows = [{"id": "field-A"}, {"id": "field-B"}, {"id": "field-C"}]
    fake_sb = _FakeSupabase(rows)

    monkeypatch.setattr(job_runner, "get_supabase_admin", lambda: fake_sb)
    monkeypatch.setattr(job_runner, "_active", {"field-B"})

    count = job_runner.reconcile_stale_processing(timeout_minutes=15)

    assert count == 2
    updated_ids = {field_id for field_id, _ in fake_sb.updates}
    assert updated_ids == {"field-A", "field-C"}
    for _field_id, payload in fake_sb.updates:
        assert payload["processing_status"] == "failed"
        assert "timed out" in payload["processing_error"]


def test_reconcile_is_a_noop_when_nothing_is_stale(monkeypatch):
    fake_sb = _FakeSupabase([])
    monkeypatch.setattr(job_runner, "get_supabase_admin", lambda: fake_sb)
    monkeypatch.setattr(job_runner, "_active", set())

    count = job_runner.reconcile_stale_processing(timeout_minutes=15)

    assert count == 0
    assert fake_sb.updates == []


def test_reconcile_excludes_every_field_this_process_still_has_active(monkeypatch):
    rows = [{"id": "field-A"}, {"id": "field-B"}]
    fake_sb = _FakeSupabase(rows)
    monkeypatch.setattr(job_runner, "get_supabase_admin", lambda: fake_sb)
    monkeypatch.setattr(job_runner, "_active", {"field-A", "field-B"})

    count = job_runner.reconcile_stale_processing(timeout_minutes=15)

    assert count == 0
    assert fake_sb.updates == []
