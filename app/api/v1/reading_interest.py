from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import ApiResponse, success_response
from app.services.reading_interest_service import ReadingInterestService

router = APIRouter(tags=["reading-interest"])
CurrentUser = Annotated[User, Depends(get_current_user)]
Database = Annotated[Session, Depends(get_db)]


class InterestUpdate(BaseModel):
    wanted: bool


class StatusRequest(BaseModel):
    book_ids: list[UUID] = Field(max_length=100)


@router.post("/api/v1/user-books/status", response_model=ApiResponse[list[dict]])
def statuses(payload: StatusRequest, request: Request, user: CurrentUser, db: Database) -> dict:
    return success_response(
        request.state.request_id, ReadingInterestService(db).statuses(user.id, payload.book_ids)
    )


@router.put("/api/v1/user-books/{book_id}/interest", response_model=ApiResponse[dict])
def set_interest(
    book_id: UUID, payload: InterestUpdate, request: Request, user: CurrentUser, db: Database
) -> dict:
    return success_response(
        request.state.request_id,
        ReadingInterestService(db).set_interest(user.id, book_id, payload.wanted),
    )


@router.get("/api/v1/user-books/wanted", response_model=ApiResponse[dict])
def wanted(
    request: Request,
    user: CurrentUser,
    db: Database,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    return success_response(
        request.state.request_id, ReadingInterestService(db).mine(user.id, page, page_size)
    )


@router.get("/api/v1/books/popular", response_model=ApiResponse[dict])
def popular(request: Request, user: CurrentUser, db: Database, days: int = Query(30)) -> dict:
    return success_response(
        request.state.request_id, ReadingInterestService(db).ranking(user.id, days, 1, 20)
    )


@router.get("/api/v1/admin/books/popular", response_model=ApiResponse[dict])
def admin_popular(
    request: Request,
    user: Annotated[User, Depends(require_admin)],
    db: Database,
    days: int = Query(30),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> dict:
    return success_response(
        request.state.request_id, ReadingInterestService(db).ranking(user.id, days, page, page_size)
    )
