from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import AppError
from app.db.models import RecommendationSet, User
from app.db.session import get_db
from app.schemas.common import ApiResponse, success_response
from app.schemas.recommendation import RecommendationSetRead, RefineRequest
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])


@router.get("/{set_id}", response_model=ApiResponse[RecommendationSetRead])
def get_recommendation(
    set_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = RecommendationService(session).get_set(set_id, current_user.id)
    if value is None:
        raise AppError(status_code=404, code="RECOMMENDATION_NOT_FOUND", message="推荐结果不存在")
    return success_response(request.state.request_id, value)


@router.post("/{set_id}/refine", response_model=ApiResponse[RecommendationSetRead])
async def refine_recommendation(
    set_id: UUID,
    payload: RefineRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    existing = session.get(RecommendationSet, set_id)
    if existing is None or existing.user_id != current_user.id:
        raise AppError(status_code=404, code="RECOMMENDATION_NOT_FOUND", message="推荐结果不存在")
    only_available = (
        payload.only_available
        if payload.only_available is not None
        else bool(existing.constraints_snapshot.get("only_available"))
    )
    value = await RecommendationService(session).recommend(
        user=current_user,
        conversation_id=existing.conversation_id,
        query=f"{existing.query}；补充要求：{payload.instruction}",
        only_available=only_available,
    )
    return success_response(request.state.request_id, value)
