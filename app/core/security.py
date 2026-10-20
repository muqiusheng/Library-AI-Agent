from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jwt import InvalidTokenError

from app.core.config import Settings, get_settings

_password_hasher = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)


def hash_password(password: str) -> str:
    if len(password) < 8:
        raise ValueError("password must contain at least 8 characters")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def create_access_token(
    *,
    user_id: UUID,
    role: str,
    settings: Settings | None = None,
    now: datetime | None = None,
) -> tuple[str, int]:
    config = settings or get_settings()
    issued_at = now or datetime.now(UTC)
    expires_delta = timedelta(minutes=config.jwt_access_token_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": issued_at,
        "exp": issued_at + expires_delta,
    }
    token = jwt.encode(payload, config.jwt_secret, algorithm=config.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str, settings: Settings | None = None) -> dict[str, Any]:
    config = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            config.jwt_secret,
            algorithms=[config.jwt_algorithm],
            options={"require": ["sub", "role", "type", "iat", "exp"]},
        )
    except InvalidTokenError as exc:
        raise ValueError("invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise ValueError("invalid token type")
    try:
        UUID(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid token subject") from exc
    return payload
