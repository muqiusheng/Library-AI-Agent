"""Persist recommendation checkpoints and resume only the requested pipeline stage."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import aclosing
from copy import deepcopy
from uuid import UUID

from sqlalchemy import select

from app.core.errors import AppError
from app.db.models import Message, MessageRole, MessageType
from app.services.conversation_service import ConversationService
from app.services.effective_profile_service import EffectiveProfileService
from app.services.recommendation_progress import (
    RecommendationProgress,
    exclude_profile_facts,
    profile_evidence,
)
from app.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


class RecommendationRunService:
    def __init__(self, session, user, conversation, user_message, request_id, progress=None):
        self.session, self.user = session, user
        self.conversation, self.user_message = conversation, user_message
        self.request_id = request_id
        self.progress = progress or RecommendationProgress(str(user_message.id))
        self.state = deepcopy((user_message.structured_payload or {}).get("recommendation_run", {}))
        self.recommendations = RecommendationService(session)

    def _save(self) -> None:
        self.state["analysis"] = self.progress.snapshot()
        self.user_message.structured_payload = {
            **(self.user_message.structured_payload or {}),
            "recommendation_run": deepcopy(self.state),
        }
        self.session.commit()

    def _checkpoint(self, data: dict) -> None:
        self.state.setdefault("checkpoint", {}).update(deepcopy(data))
        self._save()

    def _stages(self) -> list[str]:
        checkpoint = self.state.get("checkpoint", {})
        return [
            "retrieving",
            *(["comparing"] if "candidate_ids" in checkpoint else []),
            *(["generating"] if checkpoint.get("recommendation_set_id") else []),
        ]

    def _reply(self, content: str, analysis: dict, set_id: str | None = None):
        previous = self.session.scalar(
            select(Message)
            .where(
                Message.conversation_id == self.conversation.id,
                Message.role == MessageRole.ASSISTANT,
                Message.created_at > self.user_message.created_at,
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        service = ConversationService(self.session)
        if previous and (previous.structured_payload or {}).get("analysis", {}).get(
            "turn_id"
        ) == str(self.user_message.id):
            previous.content = content
            previous.message_type = MessageType.RECOMMENDATION if set_id else MessageType.TEXT
            previous.structured_payload = {
                "analysis": analysis,
                **({"recommendation_set_id": set_id} if set_id else {}),
            }
            service.repository.touch(self.conversation)
            self.session.commit()
            return previous
        if set_id:
            return service.add_recommendation_message(
                self.conversation, content, UUID(set_id), analysis=analysis
            )
        return service.add_assistant_message(self.conversation, content, analysis=analysis)

    async def stream(
        self,
        parameters: dict | None = None,
        *,
        stage="retrieving",
        excluded_profile_keys: list[str] | None = None,
        only_available: bool | None = None,
    ) -> AsyncIterator[tuple[str, dict]]:
        previous = deepcopy(self.state.get("analysis", {}))
        if parameters is not None:
            self.state = {"request": parameters, "checkpoint": {}, "attempt": 0}
        parameters = deepcopy(self.state["request"])
        previous_availability = parameters.get("constraints", {}).get(
            "only_available", parameters.get("only_available", False)
        )
        conditions_changed = only_available is not None and only_available != previous_availability
        if only_available is not None:
            parameters["only_available"] = only_available
            parameters["constraints"] = {
                **parameters.get("constraints", {}),
                "only_available": only_available,
            }
        previous_ignored = parameters.get("excluded_profile_keys", [])
        if excluded_profile_keys is not None:
            parameters["excluded_profile_keys"] = list(dict.fromkeys(excluded_profile_keys))
        ignored = parameters.get("excluded_profile_keys", [])
        checkpoint = self.state.get("checkpoint", {})
        raw_profile = EffectiveProfileService(self.session).build(self.user)
        profile = exclude_profile_facts(raw_profile, ignored)
        retry_note = ""
        if stage != "retrieving" and (
            previous_ignored != ignored
            or checkpoint.get("profile_snapshot") != profile
            or conditions_changed
        ):
            stage = "retrieving"
            retry_note = "画像、本次采用项或筛选条件已变化，已从检索重新执行以应用新信息。"
        if stage != "retrieving":
            ids = [UUID(value) for value in checkpoint.get("candidate_ids", [])]
            if len(self.recommendations.library.get_books(ids)) != len(ids):
                stage = "retrieving"
                retry_note = "馆藏版本已变化，已重新检索当前馆藏。"
        cached_recommendation = None
        if stage == "generating":
            cached_recommendation = self.recommendations.get_set(
                UUID(checkpoint["recommendation_set_id"]), self.user.id
            )
            count = previous.get("filter_stats", {}).get("selected")
            only_available = parameters.get("constraints", {}).get(
                "only_available", parameters.get("only_available", False)
            )
            if (
                cached_recommendation is None
                or (count is not None and len(cached_recommendation.items) != count)
                or (
                    only_available
                    and any(item.available_count == 0 for item in cached_recommendation.items)
                )
            ):
                stage = "retrieving"
                retry_note = "原书单或借阅状态已变化，已重新检索以满足本次条件。"
        if previous:
            self.progress.resume(previous, stage)
        self.state["request"] = parameters
        self.state["attempt"] = self.state.get("attempt", 0) + 1
        if stage == "retrieving":
            self.state["checkpoint"] = {}
        elif stage == "comparing":
            # A new comparison invalidates the previous downstream selection.
            self.state["checkpoint"].pop("recommendation_set_id", None)
        evidence = profile_evidence(raw_profile, parameters["query"], str(self.user_message.id))
        self.progress.update(
            {
                "retry_stages": self._stages(),
                "retry_note": retry_note,
                "profile_evidence": [fact for fact in evidence if fact["key"] not in ignored],
                "excluded_profile_evidence": [fact for fact in evidence if fact["key"] in ignored],
                "excluded_profile_keys": ignored,
            }
        )
        self.progress.extra["attempt"] = self.state["attempt"]
        self._save()
        yield "constraints_updated", parameters.get("constraints", {})
        yield "analysis", self.progress.snapshot()
        content = ""
        try:
            recommendation = None
            if stage == "generating":
                recommendation = cached_recommendation
                if recommendation is None:
                    raise AppError(
                        status_code=404,
                        code="RECOMMENDATION_NOT_FOUND",
                        message="原推荐结果不存在，请从检索重新执行。",
                    )
                # Refresh availability without searching or changing the chosen order.
                by_id = {str(book.book_id): book for book in recommendation.items}
                for entry in [
                    *self.progress.comparisons,
                    *self.progress.extra.get("candidates", []),
                ]:
                    if entry["book_id"] in by_id:
                        entry["available_count"] = by_id[entry["book_id"]].available_count
            else:
                arguments = {
                    **parameters,
                    "user": self.user,
                    "conversation_id": self.conversation.id,
                    "current_message_id": self.user_message.id,
                    "on_checkpoint": self._checkpoint,
                    "excluded_book_ids": [
                        UUID(value) for value in parameters.get("excluded_book_ids", [])
                    ],
                    "replacement_slots": [
                        UUID(value) if value else None
                        for value in parameters.get("replacement_slots") or []
                    ]
                    or None,
                }
                if stage == "comparing":
                    arguments["resume_candidate_ids"] = [
                        UUID(value) for value in checkpoint["candidate_ids"]
                    ]
                async with aclosing(self.recommendations.recommend_events(**arguments)) as events:
                    async for kind, data in events:
                        if kind == "progress":
                            data["retry_stages"] = self._stages()
                            self.progress.update(data)
                            self._save()
                            yield "analysis", self.progress.snapshot()
                        else:
                            recommendation = data
            if recommendation is None:
                raise RuntimeError("Recommendation result missing")
            self.progress.update({"retry_stages": self._stages()})
            yield "recommendation_ready", recommendation.model_dump(mode="json")
            yield "analysis", self.progress.update({"stage": "generating", "label": "正在生成推荐"})
            self._save()
            async for chunk in self.recommendations.stream_summary(recommendation, self.user):
                content += chunk
                yield "text_delta", {"content": chunk}
            analysis = self.progress.finish()
            self._save()
            assistant = self._reply(content, analysis, str(recommendation.id))
            yield "analysis", analysis
            yield "message_end", {"message_id": str(assistant.id), "request_id": self.request_id}
        except (asyncio.CancelledError, GeneratorExit):
            if self.progress.status == "running":
                self._save_failure(content, "stopped", "")
            raise
        except Exception as exc:
            message = exc.message if isinstance(exc, AppError) else "推荐暂时失败，请重试当前阶段。"
            self._save_failure(content, "error", message)
            yield "analysis", self.progress.snapshot()
            yield (
                "error",
                {
                    "code": exc.code if isinstance(exc, AppError) else "RECOMMENDATION_FAILED",
                    "message": message,
                    "request_id": self.request_id,
                },
            )

    def _save_failure(self, content, status, message):
        self.session.rollback()
        self.progress.update({"error_message": message, "retry_stages": self._stages()})
        analysis = self.progress.finish(status)
        try:
            self._save()
            self._reply(
                content, analysis, self.state.get("checkpoint", {}).get("recommendation_set_id")
            )
        except Exception:
            self.session.rollback()
            logger.exception("Unable to persist interrupted recommendation")
