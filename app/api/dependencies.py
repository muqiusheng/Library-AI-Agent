from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_access_token
from app.db.models import User, UserRole
from app.db.session import get_db
from app.repositories.user_repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError(
            status_code=401,
            code="AUTHENTICATION_REQUIRED",
            message="请先登录",
        )
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (TypeError, ValueError, KeyError) as exc:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="登录状态已失效，请重新登录",
        ) from exc

    user = UserRepository(session).get_by_id(user_id, with_profile=True)
    if user is None or not user.is_active:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="登录状态已失效，请重新登录",
        )
    return user


def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPER_ADMIN}:
        raise AppError(
            status_code=403,
            code="ADMIN_REQUIRED",
            message="需要管理员权限",
        )
    return current_user


def require_super_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.role != UserRole.SUPER_ADMIN:
        raise AppError(
            status_code=403,
            code="SUPER_ADMIN_REQUIRED",
            message="需要超级管理员权限",
        )
    return current_user
