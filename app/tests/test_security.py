from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_round_trip() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert password_hash != "correct horse battery staple"
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("wrong password", password_hash)


def test_short_password_is_rejected() -> None:
    with pytest.raises(ValueError, match="8"):
        hash_password("short")


def test_access_token_round_trip_and_expiry() -> None:
    settings = Settings(_env_file=None, jwt_secret="test-secret-with-at-least-32-bytes")
    user_id = uuid4()
    now = datetime.now(UTC)
    token, expires_in = create_access_token(
        user_id=user_id,
        role="student",
        settings=settings,
        now=now,
    )
    payload = decode_access_token(token, settings)
    assert payload["sub"] == str(user_id)
    assert payload["role"] == "student"
    assert expires_in == settings.jwt_access_token_minutes * 60

    expired_token, _ = create_access_token(
        user_id=user_id,
        role="student",
        settings=settings,
        now=now - timedelta(days=1),
    )
    with pytest.raises(ValueError, match="expired"):
        decode_access_token(expired_token, settings)
