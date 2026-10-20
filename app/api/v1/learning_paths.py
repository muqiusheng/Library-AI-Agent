from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import ApiResponse, success_response
from app.schemas.learning_path import (
    LearningPathCreate,
    LearningPathRead,
    LearningPathStatusUpdate,
    LearningPathSummary,
    PathBookStateUpdate,
)
from app.services.learning_path_service import LearningPathService

router = APIRouter(prefix="/api/v1/learning-paths", tags=["learning-paths"])


@router.post("", response_model=ApiResponse[LearningPathRead], status_code=status.HTTP_201_CREATED)
def create_path(
    payload: LearningPathCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = LearningPathService(session).create_from_recommendation(
        current_user.id, payload.recommendation_set_id, payload.title
    )
    return success_response(request.state.request_id, value)


@router.get("", response_model=ApiResponse[list[LearningPathSummary]])
def list_paths(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(
        request.state.request_id, LearningPathService(session).list_for_user(current_user.id)
    )


@router.get("/{path_id}", response_model=ApiResponse[LearningPathRead])
def get_path(
    path_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(
        request.state.request_id, LearningPathService(session).get_owned(path_id, current_user.id)
    )


@router.patch("/{path_id}/status", response_model=ApiResponse[LearningPathRead])
def update_status(
    path_id: UUID,
    payload: LearningPathStatusUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = LearningPathService(session).update_status(path_id, current_user.id, payload.status)
    return success_response(request.state.request_id, value)


@router.patch("/{path_id}/books/{book_id}", response_model=ApiResponse[LearningPathRead])
def update_book(
    path_id: UUID,
    book_id: UUID,
    payload: PathBookStateUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = LearningPathService(session).update_book_state(
        path_id, book_id, current_user.id, payload.state
    )
    return success_response(request.state.request_id, value)


@router.patch("/{path_id}/stages/{stage_id}/complete", response_model=ApiResponse[LearningPathRead])
def complete_stage(
    path_id: UUID,
    stage_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = LearningPathService(session).complete_stage(
        path_id, stage_id, current_user.id
    )
    return success_response(request.state.request_id, value)
