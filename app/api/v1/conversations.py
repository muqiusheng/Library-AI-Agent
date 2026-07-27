import json
from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import AppError
from app.db.models import User
from app.db.session import get_db
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.common import ApiResponse, success_response
from app.schemas.conversation import (
    ConstraintRead,
    ConstraintUpdate,
    ConversationCreate,
    ConversationSummary,
    ConversationUpdate,
    MessageCreate,
    MessageRead,
)
from app.services.conversation_constraint_service import ConversationConstraintService
from app.services.conversation_service import ConversationService
from app.services.general_chat_service import GeneralChatService
from app.services.profile_memory_service import ProfileMemoryService
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


def _event(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


@router.get("", response_model=ApiResponse[list[ConversationSummary]])
def list_conversations(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    values = ConversationRepository(session).list_for_user(current_user.id)
    return success_response(
        request.state.request_id,
        [ConversationSummary.model_validate(value) for value in values],
    )


@router.post(
    "",
    response_model=ApiResponse[ConversationSummary],
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = ConversationService(session).create(current_user, payload.title)
    return success_response(request.state.request_id, ConversationSummary.model_validate(value))


@router.patch("/{conversation_id}", response_model=ApiResponse[ConversationSummary])
def update_conversation(
    conversation_id: UUID,
    payload: ConversationUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    value = ConversationService(session).update(
        conversation_id,
        current_user,
        title=payload.title,
        archived=payload.archived,
    )
    return success_response(request.state.request_id, ConversationSummary.model_validate(value))


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> Response:
    ConversationService(session).delete(conversation_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{conversation_id}/messages", response_model=ApiResponse[list[MessageRead]])
def list_messages(
    conversation_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    values = ConversationRepository(session).messages(conversation_id, current_user.id)
    return success_response(
        request.state.request_id,
        [MessageRead.model_validate(value) for value in values],
    )


@router.post("/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    conversation = ConversationRepository(session).get_owned(conversation_id, current_user.id)
    service = ConversationService(session)
    user_message = service.add_user_message(conversation, payload.content)
    ProfileMemoryService(session).extract_from_message(current_user, user_message)
    constraints = ConversationConstraintService(session).update_from_message(
        conversation, payload.content, only_available=payload.only_available
    )
    request_id = request.state.request_id

    async def generate() -> AsyncIterator[str]:
        yield _event(
            "message_start",
            {
                "request_id": request_id,
                "message_id": str(user_message.id),
                "status": "understanding",
            },
        )
        try:
            general_chat = GeneralChatService(session)
            if not general_chat.is_library_request(payload.content):
                answer = await general_chat.answer(conversation, payload.content)
                yield _event("text_delta", {"content": answer})
                assistant_message = service.add_assistant_message(conversation, answer)
                yield _event(
                    "message_end",
                    {"message_id": str(assistant_message.id), "request_id": request_id},
                )
                return
            yield _event("message_start", {"request_id": request_id, "status": "retrieving"})
            recommendation = await RecommendationService(session).recommend(
                user=current_user,
                conversation_id=conversation.id,
                query=payload.content,
                only_available=constraints.only_available,
                constraints=constraints.model_dump(),
            )
            yield _event("message_start", {"request_id": request_id, "status": "organizing"})
            summary = recommendation.summary
            yield _event("text_delta", {"content": summary})
            assistant_message = service.add_recommendation_message(
                conversation, summary, recommendation.id
            )
            yield _event(
                "recommendation_ready",
                recommendation.model_dump(mode="json"),
            )
            yield _event(
                "message_end",
                {"message_id": str(assistant_message.id), "request_id": request_id},
            )
        except AppError as exc:
            yield _event(
                "error",
                {"code": exc.code, "message": exc.message, "request_id": request_id},
            )
        except Exception:
            yield _event(
                "error",
                {
                    "code": "RECOMMENDATION_FAILED",
                    "message": "推荐暂时失败，请重试",
                    "request_id": request_id,
                },
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/{conversation_id}/constraints", response_model=ApiResponse[ConstraintRead])
def get_constraints(
    conversation_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    conversation = ConversationRepository(session).get_owned(conversation_id, current_user.id)
    value = ConversationConstraintService(session).get(conversation)
    return success_response(request.state.request_id, value)


@router.patch("/{conversation_id}/constraints", response_model=ApiResponse[ConstraintRead])
def update_constraints(
    conversation_id: UUID,
    payload: ConstraintUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    conversation = ConversationRepository(session).get_owned(conversation_id, current_user.id)
    value = ConversationConstraintService(session).update(conversation, payload)
    return success_response(request.state.request_id, value)
