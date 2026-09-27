from app.core.config import Settings
from app.core.security import public_error_message, sanitize_health_error


def test_public_error_message_hides_details_in_production():
    settings = Settings(app_env="production")
    msg = public_error_message(RuntimeError("db password is wrong"), settings)
    assert "db password" not in msg
    assert msg == "An internal error occurred. Please try again or contact support."


def test_public_error_message_shows_details_outside_production():
    settings = Settings(app_env="development")
    msg = public_error_message(RuntimeError("db password is wrong"), settings)
    assert "db password is wrong" in msg


def test_sanitize_health_error_hides_details_when_disabled():
    settings = Settings(health_detail_enabled=False)
    msg = sanitize_health_error(RuntimeError("internal path leaked"), settings)
    assert msg == "error"


def test_sanitize_health_error_shows_details_when_enabled():
    settings = Settings(health_detail_enabled=True)
    msg = sanitize_health_error(RuntimeError("internal path leaked"), settings)
    assert "internal path leaked" in msg
