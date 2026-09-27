"""Regression test for the ALLOW_OPEN_REGISTRATION production warning
(docs/AUDIT-FINDINGS.md #4).
"""
import logging

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.config import Settings


def test_warns_when_open_registration_left_on_in_production(monkeypatch, caplog):
    monkeypatch.setattr(
        main_module, "settings", Settings(app_env="production", allow_open_registration=True)
    )
    with caplog.at_level(logging.WARNING, logger="app.main"):
        with TestClient(main_module.app):
            pass

    assert any("ALLOW_OPEN_REGISTRATION" in record.message for record in caplog.records)


def test_no_warning_when_registration_is_closed_in_production(monkeypatch, caplog):
    monkeypatch.setattr(
        main_module, "settings", Settings(app_env="production", allow_open_registration=False)
    )
    with caplog.at_level(logging.WARNING, logger="app.main"):
        with TestClient(main_module.app):
            pass

    assert not any("ALLOW_OPEN_REGISTRATION" in record.message for record in caplog.records)


def test_no_warning_in_development_even_with_open_registration(monkeypatch, caplog):
    monkeypatch.setattr(
        main_module, "settings", Settings(app_env="development", allow_open_registration=True)
    )
    with caplog.at_level(logging.WARNING, logger="app.main"):
        with TestClient(main_module.app):
            pass

    assert not any("ALLOW_OPEN_REGISTRATION" in record.message for record in caplog.records)
