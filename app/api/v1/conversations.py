import json
from collections.abc import AsyncIterator
from contextlib import aclosing
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import AppError
from app.db.models import Message, MessageRole, User
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
    RecommendationRetry,
)
from app.services.conversation_constraint_service import ConversationConstraintService
from app.services.conversation_context_service import ConversationContextService
from app.services.conversation_service import ConversationService
from app.services.conversation_turn_service import ConversationTurnService
from app.services.effective_profile_service import EffectiveProfileService
from app.services.general_chat_service import GeneralChatService
from app.services.profile_memory_service import ProfileMemoryService
from app.services.recommendation_progress import RecommendationProgress
from app.services.recommendation_run_service import RecommendationRunService

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
async def stream_message(
    conversation_id: UUID,
    payload: MessageCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    conversation = ConversationRepository(session).get_owned(conversation_id, current_user.id)
    service = ConversationService(session)
    user_message = service.add_user_message(conversation, payload.content)

    request_id = request.state.request_id

    async def generate() -> AsyncIterator[str]:
        progress = RecommendationProgress(str(user_message.id))
        yield _event(
            "message_start",
            {
                "request_id": request_id,
                "message_id": str(user_message.id),
                "status": "understanding",
            },
        )
        yield _event(
            "analysis",
            progress.update({"stage": "understanding", "label": "正在理解需求"}),
        )
        try:
            contexts = ConversationContextService(session)
            context = contexts.build(conversation, current_user)
            profiles = ProfileMemoryService(session)
            text = payload.content
            confirmation = text.strip(" 。！!\n")
            pending = context.task.pending_profile_updates
            previous = context.history[-2] if len(context.history) >= 2 else {}
            is_confirmation = pending and "是否更新画像" in previous.get("content", "")
            if is_confirmation and confirmation in {
                "是",
                "确认",
                "确认更新",
                "同意",
                "更新吧",
                "否",
                "不更新",
                "保留原画像",
            }:
                pending_request = context.task.pending_profile_request
                accepted = confirmation not in {"否", "不更新", "保留原画像"}
                updated = profiles.confirm_conflicts(current_user, pending) if accepted else False
                answer = (
                    "已更新画像。"
                    if updated
                    else (
                        "画像已发生变化，请重新说明要更新的能力。" if accepted else "已保留原画像。"
                    )
                )
                context.task.pending_profile_updates = []
                context.task.pending_profile_request = ""
                contexts.save(conversation, context)
                yield _event("text_delta", {"content": answer})
                if updated and any(
                    word in pending_request for word in ("推荐", "找书", "图书", "教材")
                ):
                    text = pending_request
                else:
                    analysis = progress.finish()
                    assistant = service.add_assistant_message(
                        conversation, answer, analysis=analysis
                    )
                    yield _event("analysis", analysis)
                    yield _event(
                        "message_end", {"message_id": str(assistant.id), "request_id": request_id}
                    )
                    return
            yield _event(
                "analysis",
                progress.update(
                    {
                        "stage": "profile",
                        "label": "正在读取学习画像",
                        "detail": "核对本次陈述与有效画像。",
                    }
                ),
            )
            await profiles.extract_from_message(current_user, user_message)
            context.profile = EffectiveProfileService(session).build(current_user)
            if profiles.conflicts:
                context.task.pending_profile_updates = profiles.conflicts
                context.task.pending_profile_request = text
                contexts.save(conversation, context)
                changes = "；".join(
                    f"{profiles.describe(item['previous_value'])} → "
                    f"{profiles.describe(item['value_json'])}"
                    for item in profiles.conflicts
                )
                answer = (
                    f"本次陈述与手工确认的画像冲突：{changes}。"
                    "是否更新画像？请回复“确认更新”或“保留原画像”。"
                )
                yield _event("text_delta", {"content": answer})
                analysis = progress.finish()
                assistant = service.add_assistant_message(conversation, answer, analysis=analysis)
                yield _event("analysis", analysis)
                yield _event(
                    "message_end", {"message_id": str(assistant.id), "request_id": request_id}
                )
                return
            turns = ConversationTurnService()
            yield _event(
                "analysis",
                progress.update({"stage": "intent", "label": "正在明确本次需求"}),
            )
            resolution = await turns.resolve(context, text)
            turns.apply(context, resolution, text)
            contexts.save(conversation, context, commit=False)
            if resolution.action in {"recommend", "refine"}:
                context.constraints = ConversationConstraintService(session).update_from_message(
                    conversation,
                    text,
                    only_available=payload.only_available,
                    commit=False,
                )
            contexts.save(conversation, context)
            yield _event("constraints_updated", context.constraints.model_dump())
            general_chat = GeneralChatService(session)
            if resolution.action not in {"recommend", "refine"}:
                yield _event(
                    "analysis",
                    progress.update({"stage": "generating", "label": "正在生成回复"}),
                )
                answer_chunks = []
                answer = None
                if resolution.action == "clarify":
                    answer = resolution.clarification or "请补充你想找的图书主题或具体书名。"
                elif resolution.action in {"availability", "explain"} and resolution.target_rank:
                    book = context.recommendation.items[resolution.target_rank - 1]
                    if resolution.action == "availability":
                        answer = f"《{book.title}》当前有 {book.available_count} 个可借副本。"
                        locations = [
                            holding.current_location or holding.collection_location
                            for holding in book.holdings
                            if holding.book_status == "available"
                            and holding.circulation_status == "lendable"
                        ]
                        if any(locations):
                            answer += (
                                " 馆藏位置："
                                + "、".join(dict.fromkeys(filter(None, locations)))
                                + "。"
                            )
                    elif not general_chat.provider.available:
                        answer = f"《{book.title}》：{book.reason}"
                elif resolution.action == "explain" and not general_chat.provider.available:
                    answer = (
                        "\n".join(
                            f"《{book.title}》：{book.reason}"
                            for book in context.recommendation.items
                        )
                        if context.recommendation
                        else "当前还没有图书推荐结果。"
                    )
                if answer is not None:
                    answer_chunks.append(answer)
                    yield _event("text_delta", {"content": answer})
                else:
                    async for chunk in general_chat.stream_answer(
                        conversation,
                        current_user,
                        text,
                        context=context,
                    ):
                        answer_chunks.append(chunk)
                        yield _event("text_delta", {"content": chunk})

                answer = "".join(answer_chunks)
                analysis = progress.finish()
                assistant_message = service.add_assistant_message(
                    conversation, answer, analysis=analysis
                )
                yield _event("analysis", analysis)
                yield _event(
                    "message_end",
                    {"message_id": str(assistant_message.id), "request_id": request_id},
                )
                return
            yield _event("message_start", {"request_id": request_id, "status": "retrieving"})
            excluded_ids = list(context.task.excluded_book_ids)
            slots = None
            if resolution.action == "refine" and context.recommendation:
                previous_ids = [item.book_id for item in context.recommendation.items]
                if resolution.target_rank is not None:
                    rejected_id = previous_ids[resolution.target_rank - 1]
                    excluded_ids.append(rejected_id)
                    context.task.excluded_book_ids = list(dict.fromkeys(excluded_ids))
                    slots = [
                        None if i == resolution.target_rank - 1 else book_id
                        for i, book_id in enumerate(previous_ids)
                    ]
                elif any(word in text for word in ("换一批", "换一些", "还有别的")):
                    excluded_ids.extend(previous_ids)
            contexts.save(conversation, context)
            parameters = {
                "query": turns.query(context),
                "only_available": context.constraints.only_available,
                "constraints": context.constraints.model_dump(),
                "excluded_book_ids": [str(value) for value in excluded_ids],
                "replacement_slots": [str(value) if value else None for value in slots]
                if slots
                else None,
                "excluded_profile_keys": [],
            }
            run = RecommendationRunService(
                session, current_user, conversation, user_message, request_id, progress
            )
            async with aclosing(run.stream(parameters)) as events:
                async for kind, data in events:
                    yield _event(kind, data)
        except AppError as exc:
            yield _event("analysis", progress.finish("error"))
            yield _event(
                "error",
                {"code": exc.code, "message": exc.message, "request_id": request_id},
            )
        except Exception:
            import traceback

            traceback.print_exc()
            yield _event("analysis", progress.finish("error"))
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


@router.post("/{conversation_id}/messages/{message_id}/retry")
async def retry_recommendation(
    conversation_id: UUID,
    message_id: UUID,
    payload: RecommendationRetry,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> StreamingResponse:
    conversation = ConversationRepository(session).get_owned(conversation_id, current_user.id)
    message = session.get(Message, message_id)
    if (
        message is None
        or message.conversation_id != conversation.id
        or message.role != MessageRole.USER
    ):
        raise AppError(status_code=404, code="MESSAGE_NOT_FOUND", message="原始请求不存在")
    latest = session.scalar(
        select(Message.id)
        .where(Message.conversation_id == conversation.id, Message.role == MessageRole.USER)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .limit(1)
    )
    if latest != message_id:
        raise AppError(
            status_code=409, code="TURN_SUPERSEDED", message="请对最新一轮推荐进行操作。"
        )
    run = RecommendationRunService(
        session, current_user, conversation, message, request.state.request_id
    )
    if not run.state.get("request"):
        raise AppError(
            status_code=409, code="NO_CHECKPOINT", message="此请求没有可恢复的推荐记录。"
        )
    if payload.stage not in run._stages():
        raise AppError(
            status_code=409, code="NO_CHECKPOINT", message="此阶段尚未完成前置步骤，请从检索重试。"
        )
    if payload.excluded_profile_keys is not None:
        profile = EffectiveProfileService(session).build(current_user)
        allowed = {"major", "interests", "learning_goals", "difficulty_preference"}
        allowed.update(f"topic:{key}" for key in profile.get("abilities", {}))
        allowed.update(run.state["request"].get("excluded_profile_keys", []))
        if set(payload.excluded_profile_keys) - allowed:
            raise AppError(
                status_code=422, code="INVALID_PROFILE_FACT", message="本次排除项无效，请刷新画像。"
            )

    if payload.only_available is not None:
        ConversationConstraintService(session).update(
            conversation, ConstraintUpdate(only_available=payload.only_available)
        )

    async def generate() -> AsyncIterator[str]:
        async with aclosing(
            run.stream(
                stage=payload.stage,
                excluded_profile_keys=payload.excluded_profile_keys,
                only_available=payload.only_available,
            )
        ) as events:
            async for kind, data in events:
                yield _event(kind, data)

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
