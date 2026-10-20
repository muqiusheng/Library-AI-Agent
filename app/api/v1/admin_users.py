from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_super_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin_users import (
    AdminCreateRequest,
    ManagedUserRead,
    ManagedUserUpdate,
    PasswordResetRequest,
    RegistrationInviteGenerated,
    RegistrationInviteStatus,
)
from app.schemas.common import ApiResponse, success_response
from app.services.admin_user_service import AdminUserService
from app.services.registration_invite_service import RegistrationInviteService

router = APIRouter(prefix="/api/v1/admin/users", tags=["admin-users"])


@router.get(
    "/registration-invite", response_model=ApiResponse[RegistrationInviteStatus]
)
def registration_invite_status(
    request: Request,
    _: Annotated[User, Depends(require_super_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    configured, updated_at = RegistrationInviteService(session).status()
    return success_response(
        request.state.request_id,
        RegistrationInviteStatus(configured=configured, updated_at=updated_at),
    )


@router.post(
    "/registration-invite/generate",
    response_model=ApiResponse[RegistrationInviteGenerated],
)
def generate_registration_invite(
    request: Request,
    current_admin: Annotated[User, Depends(require_super_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    code, updated_at = RegistrationInviteService(session).generate(current_admin.id)
    return success_response(
        request.state.request_id,
        RegistrationInviteGenerated(configured=True, updated_at=updated_at, code=code),
    )


@router.get("", response_model=ApiResponse[list[ManagedUserRead]])
def list_users(
    request: Request,
    _: Annotated[User, Depends(require_super_admin)],
    session: Annotated[Session, Depends(get_db)],
    query: str | None = Query(default=None, max_length=100),
) -> dict:
    return success_response(
        request.state.request_id, AdminUserService(session).list_users(query)
    )


@router.post(
    "/admins", response_model=ApiResponse[ManagedUserRead], status_code=status.HTTP_201_CREATED
)
def create_admin(
    payload: AdminCreateRequest,
    request: Request,
    _: Annotated[User, Depends(require_super_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(
        request.state.request_id, AdminUserService(session).create_admin(payload)
    )


@router.patch("/{user_id}", response_model=ApiResponse[ManagedUserRead])
def update_user(
    user_id: UUID,
    payload: ManagedUserUpdate,
    request: Request,
    current_admin: Annotated[User, Depends(require_super_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = AdminUserService(session).update_user(user_id, payload, current_admin)
    return success_response(request.state.request_id, value)


@router.post("/{user_id}/reset-password", response_model=ApiResponse[ManagedUserRead])
def reset_password(
    user_id: UUID,
    payload: PasswordResetRequest,
    request: Request,
    _: Annotated[User, Depends(require_super_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = AdminUserService(session).reset_password(
        user_id, payload.password.get_secret_value()
    )
    return success_response(request.state.request_id, value)
