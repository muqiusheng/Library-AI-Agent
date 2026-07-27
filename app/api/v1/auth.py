from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.security import create_access_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RegisterRequest,
    TokenResponse,
    UserSummary,
)
from app.schemas.common import ApiResponse, success_response
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[UserSummary],
    status_code=status.HTTP_201_CREATED,
)
def register(
    payload: RegisterRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    user = AuthService(session).register(payload)
    return success_response(request.state.request_id, UserSummary.model_validate(user))


@router.post("/login", response_model=ApiResponse[TokenResponse])
def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    user = AuthService(session).authenticate(
        payload.student_no, payload.password.get_secret_value()
    )
    token, expires_in = create_access_token(user_id=user.id, role=user.role.value)
    data = TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserSummary.model_validate(user),
    )
    return success_response(request.state.request_id, data)


@router.get("/me", response_model=ApiResponse[UserSummary])
def me(
    request: Request, current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    return success_response(request.state.request_id, UserSummary.model_validate(current_user))


@router.post("/logout", response_model=ApiResponse[LogoutResponse])
def logout(request: Request, _: Annotated[User, Depends(get_current_user)]) -> dict:
    return success_response(request.state.request_id, LogoutResponse())
