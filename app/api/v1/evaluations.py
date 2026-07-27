from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import ApiResponse, success_response
from app.schemas.evaluation import EvaluationCreate, EvaluationRead, EvaluationSummary
from app.services.evaluation_service import EvaluationService

router = APIRouter(tags=["evaluations"])


@router.post(
    "/api/v1/evaluations",
    response_model=ApiResponse[EvaluationRead],
    status_code=status.HTTP_201_CREATED,
)
def create_evaluation(
    payload: EvaluationCreate,
    request: Request,
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = EvaluationService(session).create(payload)
    return success_response(request.state.request_id, EvaluationRead.model_validate(value))


@router.get(
    "/api/v1/admin/evaluations/summary", response_model=ApiResponse[EvaluationSummary]
)
def evaluation_summary(
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(request.state.request_id, EvaluationService(session).summary())


@router.get(
    "/api/v1/admin/evaluations", response_model=ApiResponse[list[EvaluationRead]]
)
def list_evaluations(
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    values = EvaluationService(session).list_records(limit, offset)
    return success_response(
        request.state.request_id, [EvaluationRead.model_validate(value) for value in values]
    )
