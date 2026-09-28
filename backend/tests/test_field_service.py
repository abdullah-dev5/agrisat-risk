"""Regression test for the latent IDOR trap in process_field
(docs/AUDIT-FINDINGS.md #13) -- process_field now takes and enforces
institution_id itself instead of relying entirely on callers to have already
checked ownership.
"""
import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services import field_service


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeFieldsTable:
    """Behaves like the real query: .eq("institution_id", X) filters results,
    so a field that exists but belongs to a different institution returns no
    rows -- exactly the case this test is defending against.
    """

    def __init__(self, rows):
        self._rows = rows
        self._filtered = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, field, value):
        self._filtered = [r for r in self._filtered if r.get(field) == value]
        return self

    def limit(self, *_a, **_k):
        return self

    def execute(self):
        return _FakeResp(self._filtered)


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, name):
        assert name == "fields"
        return _FakeFieldsTable(self.rows)


def test_process_field_rejects_a_field_belonging_to_another_institution(monkeypatch):
    # Field exists, but under a different institution than the one requesting it.
    fake_sb = _FakeSupabase([{"id": "field-1", "institution_id": "institution-A", "sowing_date": "2025-11-15"}])
    monkeypatch.setattr(field_service, "get_supabase_admin", lambda: fake_sb)

    with pytest.raises(HTTPException) as exc_info:
        field_service.process_field("field-1", "institution-B", Settings())

    assert exc_info.value.status_code == 404


def test_process_field_rejects_a_nonexistent_field(monkeypatch):
    fake_sb = _FakeSupabase([])
    monkeypatch.setattr(field_service, "get_supabase_admin", lambda: fake_sb)

    with pytest.raises(HTTPException) as exc_info:
        field_service.process_field("nonexistent", "institution-A", Settings())

    assert exc_info.value.status_code == 404
