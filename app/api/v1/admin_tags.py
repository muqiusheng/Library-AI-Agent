from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import ApiResponse, success_response
from app.schemas.tag_review import (
    AITagRequest,
    AITagRunResult,
    TagBulkReview,
    TagReviewRead,
    TagReviewUpdate,
)
from app.services.ai_tagging_service import AITaggingService, TagReviewService

router = APIRouter(prefix="/api/v1/admin/tags", tags=["admin-tags"])


@router.post("/generate", response_model=ApiResponse[AITagRunResult])
async def generate_tags(
    payload: AITagRequest,
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = await AITaggingService(session).run(payload.data_version_id, payload.limit)
    return success_response(request.state.request_id, value)


@router.get("/reviews", response_model=ApiResponse[list[TagReviewRead]])
def list_reviews(
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    values = TagReviewService(session).list_pending(limit, offset)
    return success_response(request.state.request_id, values)


@router.patch("/reviews/{tag_id}", response_model=ApiResponse[TagReviewRead])
def update_review(
    tag_id: UUID,
    payload: TagReviewUpdate,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = TagReviewService(session).update(
        tag_id,
        current_admin.id,
        payload.tag_type,
        payload.tag_value,
        payload.review_status,
    )
    return success_response(request.state.request_id, value)


@router.post("/reviews/bulk", response_model=ApiResponse[dict])
def bulk_review(
    payload: TagBulkReview,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    count = TagReviewService(session).bulk_review(payload.tag_ids, current_admin.id, payload.status)
    return success_response(request.state.request_id, {"updated": count})
