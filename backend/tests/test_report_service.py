"""Regression test for the N+1 fix in portfolio report generation
(docs/AUDIT-FINDINGS.md #3) -- proves risk_assessments is queried exactly
once per report, not once per field, using a fake Supabase client.
"""
from app.services import report_service


class _FakeResp:
    def __init__(self, data):
        self.data = data


class _FakeFieldsTable:
    def __init__(self, rows):
        self._rows = rows

    def select(self, *_a, **_k):
        return self

    def eq(self, *_a, **_k):
        return self

    def order(self, *_a, **_k):
        return self

    def execute(self):
        return _FakeResp(self._rows)


class _FakeAssessmentsTable:
    def __init__(self, rows):
        self._rows = rows
        self._filtered = rows

    def select(self, *_a, **_k):
        return self

    def in_(self, field, values):
        values = set(values)
        self._filtered = [r for r in self._filtered if r.get(field) in values]
        return self

    def eq(self, field, value):
        self._filtered = [r for r in self._filtered if r.get(field) == value]
        return self

    def execute(self):
        return _FakeResp(self._filtered)


class _FakeSupabase:
    def __init__(self, fields_rows, assessment_rows):
        self.fields_rows = fields_rows
        self.assessment_rows = assessment_rows
        self.risk_assessments_table_calls = 0

    def table(self, name):
        if name == "fields":
            return _FakeFieldsTable(self.fields_rows)
        if name == "risk_assessments":
            self.risk_assessments_table_calls += 1
            return _FakeAssessmentsTable(self.assessment_rows)
        raise AssertionError(f"unexpected table: {name}")


FIELDS = [
    {
        "id": "f1", "name": "Field One", "crop_type": "wheat", "sowing_date": "2025-11-01",
        "area_hectares": 2.0, "farmer_ref_id": "FR1", "loan_ref_id": "LN1",
    },
    {
        "id": "f2", "name": "Field Two", "crop_type": "wheat", "sowing_date": "2025-11-05",
        "area_hectares": 3.0, "farmer_ref_id": "FR2", "loan_ref_id": "LN2",
    },
]

ASSESSMENTS = [
    {"field_id": "f1", "risk_tier": "watch", "z_score": -1.1, "explanation": "watch explanation", "is_current": True},
    {"field_id": "f2", "risk_tier": "normal", "z_score": 0.2, "explanation": "normal explanation", "is_current": True},
]


def test_portfolio_csv_queries_risk_assessments_exactly_once(monkeypatch):
    fake_sb = _FakeSupabase(FIELDS, ASSESSMENTS)
    monkeypatch.setattr(report_service, "get_supabase_admin", lambda: fake_sb)

    csv_text = report_service.generate_portfolio_csv("inst-1")

    assert fake_sb.risk_assessments_table_calls == 1
    assert "watch" in csv_text
    assert "normal" in csv_text
    assert "f1" in csv_text and "f2" in csv_text


def test_portfolio_pdf_queries_risk_assessments_exactly_once(monkeypatch):
    fake_sb = _FakeSupabase(FIELDS, ASSESSMENTS)
    monkeypatch.setattr(report_service, "get_supabase_admin", lambda: fake_sb)

    pdf_bytes = report_service.generate_portfolio_pdf("inst-1")

    assert fake_sb.risk_assessments_table_calls == 1
    assert pdf_bytes.startswith(b"%PDF")


def test_portfolio_csv_handles_a_field_with_no_current_assessment(monkeypatch):
    fake_sb = _FakeSupabase(FIELDS, [ASSESSMENTS[0]])  # f2 has no assessment row
    monkeypatch.setattr(report_service, "get_supabase_admin", lambda: fake_sb)

    csv_text = report_service.generate_portfolio_csv("inst-1")

    assert fake_sb.risk_assessments_table_calls == 1
    rows = csv_text.strip().splitlines()
    f2_row = next(r for r in rows if r.startswith("f2,"))
    # empty risk_tier/z_score/explanation fields, not a crash
    assert f2_row.endswith(",,,")
