from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Body, Depends, Header, Query, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin_pipeline import ImportBatchRead, ImportIssueRead, ImportUploadResult
from app.schemas.common import ApiResponse, success_response
from app.services.admin_pipeline_service import AdminPipelineService

router = APIRouter(prefix="/api/v1/admin/imports", tags=["admin-imports"])


@router.post(
    "", response_model=ApiResponse[ImportUploadResult], status_code=status.HTTP_202_ACCEPTED
)
def upload_import(
    background_tasks: BackgroundTasks,
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    file_name: Annotated[str, Header(alias="X-File-Name", max_length=255)],
    content: Annotated[
        bytes, Body(media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    ],
) -> dict:
    batch, duplicate = AdminPipelineService(session).accept_upload(file_name, content)
    if not duplicate:
        background_tasks.add_task(AdminPipelineService.run_import, batch.id)
    return success_response(
        request.state.request_id,
        ImportUploadResult(batch=ImportBatchRead.model_validate(batch), duplicate_file=duplicate),
    )


@router.get("", response_model=ApiResponse[list[ImportBatchRead]])
def list_imports(
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    values = AdminPipelineService(session).list_batches()
    return success_response(
        request.state.request_id, [ImportBatchRead.model_validate(value) for value in values]
    )


@router.get("/{batch_id}", response_model=ApiResponse[ImportBatchRead])
def get_import(
    batch_id: UUID,
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = AdminPipelineService(session).get_batch(batch_id)
    return success_response(request.state.request_id, ImportBatchRead.model_validate(value))


@router.get("/{batch_id}/issues", response_model=ApiResponse[list[ImportIssueRead]])
def list_issues(
    batch_id: UUID,
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict:
    values = AdminPipelineService(session).list_issues(batch_id, limit, offset)
    return success_response(
        request.state.request_id, [ImportIssueRead.model_validate(value) for value in values]
    )


@router.post("/{batch_id}/publish", response_model=ApiResponse[ImportBatchRead])
def publish_import(
    batch_id: UUID,
    background_tasks: BackgroundTasks,
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = AdminPipelineService(session).queue_publish(batch_id)
    background_tasks.add_task(AdminPipelineService.run_publish, batch_id)
    return success_response(request.state.request_id, ImportBatchRead.model_validate(value))
