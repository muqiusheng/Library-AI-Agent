from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.models import User
from app.db.session import get_db
from app.schemas.admin_system import (
    AdminOverview,
    AIProviderStatus,
    AIProviderUpdate,
    SettingsUpdateRequest,
    SystemSettingRead,
)
from app.schemas.common import ApiResponse, success_response
from app.services.system_config_service import SystemConfigService

router = APIRouter(prefix="/api/v1/admin/system", tags=["admin-system"])


@router.get("/ai-provider", response_model=ApiResponse[AIProviderStatus])
def ai_provider_status(
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(
        request.state.request_id, SystemConfigService(session).get_ai_provider_status()
    )


@router.put("/ai-provider", response_model=ApiResponse[AIProviderStatus])
def update_ai_provider(
    payload: AIProviderUpdate,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = SystemConfigService(session).update_ai_provider(payload, current_admin.id)
    return success_response(request.state.request_id, value)


@router.get("/overview", response_model=ApiResponse[AdminOverview])
def overview(
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(request.state.request_id, SystemConfigService(session).overview())


@router.get("/settings", response_model=ApiResponse[list[SystemSettingRead]])
def list_settings(
    request: Request,
    _: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    return success_response(request.state.request_id, SystemConfigService(session).list_settings())


@router.patch("/settings", response_model=ApiResponse[list[SystemSettingRead]])
def update_settings(
    payload: SettingsUpdateRequest,
    request: Request,
    current_admin: Annotated[User, Depends(require_admin)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    values = SystemConfigService(session).update_many(payload.settings, current_admin.id)
    return success_response(request.state.request_id, values)
