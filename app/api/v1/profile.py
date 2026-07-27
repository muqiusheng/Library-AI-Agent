from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.repositories.profile_repository import ProfileRepository
from app.schemas.auth import ProfileSummary
from app.schemas.common import ApiResponse, success_response
from app.schemas.profile import MemoryRead, MemoryUpdate, ProfileDetail, ProfileUpdate
from app.services.profile_memory_service import ProfileMemoryService

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


@router.get("", response_model=ApiResponse[ProfileDetail])
def get_profile(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
    include_history: bool = Query(default=False),
) -> dict:
    memories = ProfileRepository(session).list_memories(
        current_user.id, include_inactive=include_history
    )
    return success_response(
        request.state.request_id,
        ProfileDetail(
            profile=(
                ProfileSummary.model_validate(current_user.profile)
                if current_user.profile is not None
                else None
            ),
            memories=[MemoryRead.model_validate(value) for value in memories],
        ),
    )


@router.patch("", response_model=ApiResponse[ProfileDetail])
def update_profile(
    payload: ProfileUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    ProfileMemoryService(session).update_profile(current_user, payload)
    memories = ProfileRepository(session).list_memories(current_user.id, include_inactive=False)
    return success_response(
        request.state.request_id,
        ProfileDetail(
            profile=ProfileSummary.model_validate(current_user.profile),
            memories=[MemoryRead.model_validate(value) for value in memories],
        ),
    )


@router.patch("/memories/{memory_id}", response_model=ApiResponse[MemoryRead])
def update_memory(
    memory_id: UUID,
    payload: MemoryUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    memory = ProfileMemoryService(session).edit_memory(
        current_user.id, memory_id, payload.value_json
    )
    return success_response(request.state.request_id, MemoryRead.model_validate(memory))


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory(
    memory_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    ProfileMemoryService(session).deactivate_memory(current_user.id, memory_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
