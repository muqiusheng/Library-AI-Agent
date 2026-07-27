from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import ApiResponse, success_response
from app.schemas.engagement import (
    BookStateRead,
    BookStateUpdate,
    FeedbackCreate,
    FeedbackRead,
)
from app.services.engagement_service import EngagementService

router = APIRouter(tags=["engagement"])


@router.post(
    "/api/v1/recommendations/{set_id}/feedback",
    response_model=ApiResponse[FeedbackRead],
)
def add_feedback(
    set_id: UUID,
    payload: FeedbackCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = EngagementService(session).add_feedback(current_user.id, set_id, payload)
    return success_response(request.state.request_id, FeedbackRead.model_validate(value))


@router.put("/api/v1/user-books/{book_id}/state", response_model=ApiResponse[BookStateRead])
def set_book_state(
    book_id: UUID,
    payload: BookStateUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = EngagementService(session).set_book_state(current_user.id, book_id, payload.state)
    return success_response(request.state.request_id, BookStateRead.model_validate(value))
