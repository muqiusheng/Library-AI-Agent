import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cors_wildcard_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(app_frontend_origins=["*"])


def test_default_deepseek_models_match_project_contract() -> None:
    settings = Settings(_env_file=None)
    assert settings.deepseek_chat_model == "deepseek-v4-flash"
    assert settings.deepseek_reasoning_model == "deepseek-v4-pro"


def test_production_rejects_default_secrets_and_disabled_rate_limit() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", _env_file=None)

    with pytest.raises(ValidationError, match="RATE_LIMIT_ENABLED"):
        Settings(
            app_env="production",
            jwt_secret="production-jwt-secret-with-at-least-32-bytes",
            database_url="postgresql+psycopg://bookpath:generated@postgres:5432/bookpath",
            registration_enabled=False,
            _env_file=None,
        )


def test_production_can_open_rate_limited_registration_without_invite_code() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret="production-jwt-secret-with-at-least-32-bytes",
        database_url="postgresql+psycopg://bookpath:generated@postgres:5432/bookpath",
        registration_enabled=True,
        rate_limit_enabled=True,
        _env_file=None,
    )
    assert settings.registration_invite_code == ""


def test_secure_production_settings_are_accepted() -> None:
    settings = Settings(
        app_env="production",
        jwt_secret="production-jwt-secret-with-at-least-32-bytes",
        database_url="postgresql+psycopg://bookpath:generated@postgres:5432/bookpath",
        registration_enabled=False,
        rate_limit_enabled=True,
        _env_file=None,
    )
    assert settings.max_account_count == 50
