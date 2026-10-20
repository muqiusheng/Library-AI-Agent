from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import ApiResponse, success_response
from app.schemas.reservation import (
    NotificationRead,
    ReservationCreate,
    ReservationRead,
    UnreadCount,
)
from app.services.reservation_service import NotificationService, ReservationService

router = APIRouter(tags=["reservations", "notifications"])


@router.post("/api/v1/reservations", response_model=ApiResponse[ReservationRead])
def create_reservation(
    payload: ReservationCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = ReservationService(session).create(current_user.id, payload.holding_id)
    return success_response(request.state.request_id, value)


@router.get("/api/v1/reservations", response_model=ApiResponse[list[ReservationRead]])
def list_reservations(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(
        request.state.request_id, ReservationService(session).list_for_user(current_user.id)
    )


@router.delete("/api/v1/reservations/{reservation_id}", response_model=ApiResponse[ReservationRead])
def cancel_reservation(
    reservation_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = ReservationService(session).cancel(current_user.id, reservation_id)
    return success_response(request.state.request_id, value)


@router.get("/api/v1/notifications", response_model=ApiResponse[list[NotificationRead]])
def list_notifications(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
    unread_only: bool = False,
) -> dict:
    values = NotificationService(session).list_for_user(current_user.id, unread_only)
    return success_response(
        request.state.request_id, [NotificationRead.model_validate(value) for value in values]
    )


@router.get("/api/v1/notifications/unread-count", response_model=ApiResponse[UnreadCount])
def unread_count(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    count = NotificationService(session).unread_count(current_user.id)
    return success_response(request.state.request_id, UnreadCount(count=count))


@router.patch(
    "/api/v1/notifications/{notification_id}/read", response_model=ApiResponse[NotificationRead]
)
def mark_read(
    notification_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = NotificationService(session).mark_read(current_user.id, notification_id)
    return success_response(request.state.request_id, NotificationRead.model_validate(value))


@router.post("/api/v1/notifications/read-all", response_model=ApiResponse[dict])
def mark_all_read(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    count = NotificationService(session).mark_all_read(current_user.id)
    return success_response(request.state.request_id, {"updated": count})
