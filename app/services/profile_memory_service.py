import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import MemorySource, Message, MessageRole, ProfileMemory, User
from app.integrations.llm.deepseek import DeepSeekProvider
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileUpdate
from app.services.effective_profile_service import (
    EffectiveProfileService,
    normalize_fact,
    revision_time,
)
from app.services.profile_fact_extractor import (
    ExtractedMemory,
    ProfileExtraction,
    explicit_foundation,
    validate_fact,
)

logger = logging.getLogger(__name__)


class ProfileMemoryService:
    def __init__(self, session: Session, provider: DeepSeekProvider | None = None) -> None:
        self.session = session
        self.repository = ProfileRepository(session)
        self.provider = provider or DeepSeekProvider()
        self.conflicts: list[dict] = []

    async def extract_from_message(self, user: User, message: Message) -> list[ProfileMemory]:
        self.conflicts = []
        if message.role != MessageRole.USER or not self.provider.available:
            return []
        history = [
            {"role": item.role.value, "content": item.content}
            for item in ConversationRepository(self.session).recent_messages(
                message.conversation_id,
                user.id,
                limit=8,
                before=message.created_at,
            )
            if item.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
        extracted = await self._extract_async(message.content, history=history)
        created = []
        for value in extracted:
            memory = self._replace_active(
                user_id=user.id,
                category=value.category,
                key=value.key,
                value=value.value,
                source=MemorySource.CONVERSATION,
                confidence=value.confidence,
                source_message_id=message.id,
                user_edited=False,
                protect_manual=True,
                operation=value.operation,
            )
            if memory is not None:
                created.append(memory)
        if created:
            self.session.commit()
        return created

    def update_profile(self, user: User, payload: ProfileUpdate) -> None:
        if user.profile is None:
            raise AppError(status_code=404, code="PROFILE_NOT_FOUND", message="画像不存在")
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if value is None and field != "career_direction":
                raise AppError(
                    status_code=422, code="INVALID_PROFILE_FACT", message="必填画像字段不能置空"
                )
            setattr(user.profile, field, value)
            if field == "foundation":
                self._clear_abilities(user.id)
            self._replace_active(
                user_id=user.id,
                category="profile",
                key=field,
                value=value if value is not None else "",
                source=MemorySource.MANUAL,
                confidence=1.0,
                source_message_id=None,
                user_edited=True,
                protect_manual=False,
            )
            if field == "foundation":
                for ability in explicit_foundation(value):
                    self._replace_active(
                        user_id=user.id,
                        category="foundation",
                        key=ability["topic"],
                        value=ability,
                        source=MemorySource.MANUAL,
                        confidence=1.0,
                        source_message_id=None,
                        user_edited=True,
                        protect_manual=False,
                    )
        self.session.commit()

    def edit_memory(self, user_id: UUID, memory_id: UUID, value: Any) -> ProfileMemory:
        existing = self.repository.get_owned_memory(memory_id, user_id)
        if existing is None:
            raise AppError(status_code=404, code="MEMORY_NOT_FOUND", message="画像记忆不存在")
        if existing.category == "profile" and existing.key == "foundation":
            self._clear_abilities(user_id)
        created = self._replace_active(
            user_id=user_id,
            category=existing.category,
            key=existing.key,
            value=value,
            source=MemorySource.MANUAL,
            confidence=1.0,
            source_message_id=None,
            user_edited=True,
            protect_manual=False,
        )
        if (
            existing.category == "profile"
            and existing.key == "foundation"
            and isinstance(value, str)
        ):
            for ability in explicit_foundation(value):
                self._replace_active(
                    user_id=user_id,
                    category="foundation",
                    key=ability["topic"],
                    value=ability,
                    source=MemorySource.MANUAL,
                    confidence=1.0,
                    source_message_id=None,
                    user_edited=True,
                    protect_manual=False,
                )
        self.session.commit()
        return created or existing

    def deactivate_memory(self, user_id: UUID, memory_id: UUID) -> None:
        self._lock(user_id)
        memory = self.repository.get_owned_memory(memory_id, user_id)
        if memory is None:
            raise AppError(status_code=404, code="MEMORY_NOT_FOUND", message="画像记忆不存在")
        if not memory.is_active:
            return
        try:
            category, key, _ = normalize_fact(memory.category, memory.key, memory.value_json)
        except (ValueError, TypeError, AttributeError):
            memory.is_active = False
            self.session.commit()
            return
        for revision in (
            EffectiveProfileService(self.session).revisions(user_id).get((category, key), [])
        ):
            revision.is_active = False
        self.session.commit()

    def _lock(self, user_id: UUID) -> None:
        self.session.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        ).scalar_one()

    def _clear_abilities(self, user_id: UUID) -> None:
        self._lock(user_id)
        for (category, _), revisions in (
            EffectiveProfileService(self.session).revisions(user_id).items()
        ):
            if category == "foundation":
                for memory in revisions:
                    memory.is_active = False
        self.session.flush()

    @staticmethod
    def describe(value: Any) -> str:
        if isinstance(value, dict) and "level" in value:
            labels = {
                "none": "未学习",
                "basic": "有基础",
                "intermediate": "中等水平",
                "advanced": "进阶水平",
                "unknown": "尚不确定",
            }
            return value.get("topic", "") + "：" + labels.get(value["level"], value["level"])
        if isinstance(value, list):
            return "、".join(value) or "无"
        return str(value)

    def confirm_conflicts(self, user: User, proposals: list[dict]) -> bool:
        self._lock(user.id)
        winners = EffectiveProfileService(self.session).winners(user.id)
        for proposal in proposals:
            current = winners.get((proposal["category"], proposal["key"]))
            if current is None or str(current.id) != proposal["protected_memory_id"]:
                return False
        for proposal in proposals:
            self._replace_active(
                user_id=user.id,
                category=proposal["category"],
                key=proposal["key"],
                value=proposal["value_json"],
                source=MemorySource.MANUAL,
                confidence=1.0,
                source_message_id=None,
                user_edited=True,
                protect_manual=False,
            )
        self.session.commit()
        return True

    def _replace_active(
        self,
        *,
        user_id: UUID,
        category: str,
        key: str,
        value: Any,
        source: MemorySource,
        confidence: float,
        source_message_id: UUID | None,
        user_edited: bool,
        protect_manual: bool,
        operation: str = "set",
    ) -> ProfileMemory | None:
        self._lock(user_id)
        try:
            category, key, value = normalize_fact(category, key, value)
        except (TypeError, ValueError, AttributeError) as exc:
            raise AppError(
                status_code=422, code="INVALID_PROFILE_FACT", message="画像事实格式不正确"
            ) from exc
        effective = EffectiveProfileService(self.session)
        revisions = effective.revisions(user_id).get((category, key), [])
        existing = effective.winners(user_id).get((category, key))
        if category in {"interests", "learning_goals"} and operation != "set":
            user = self.session.get(User, user_id)
            current_values = effective.build(user)[category]
            if operation == "remove":
                removed = {item.casefold() for item in value}
                value = [item for item in current_values if item.casefold() not in removed]
            else:
                value = list(dict.fromkeys([*current_values, *value]))
        if existing is not None:
            _, _, old_value = normalize_fact(existing.category, existing.key, existing.value_json)
            if old_value == value and (existing.is_user_edited or not user_edited):
                return None
            if protect_manual and existing.is_user_edited:
                self.conflicts.append(
                    {
                        "category": category,
                        "key": key,
                        "value_json": value,
                        "protected_memory_id": str(existing.id),
                        "previous_value": old_value,
                    }
                )
                return None
        for revision in revisions:
            revision.is_active = False
        latest = self.session.scalar(
            select(ProfileMemory)
            .where(ProfileMemory.user_id == user_id)
            .order_by(ProfileMemory.created_at.desc())
            .limit(1)
        )
        created_at = max(
            [
                datetime.now(UTC),
                *(revision_time(revision) + timedelta(microseconds=1) for revision in revisions),
                *([revision_time(latest) + timedelta(microseconds=1)] if latest else []),
            ]
        )
        memory = ProfileMemory(
            user_id=user_id,
            category=category,
            key=key,
            value_json=value,
            source=source,
            source_message_id=source_message_id,
            confidence=confidence,
            is_active=True,
            is_user_edited=user_edited,
            created_at=created_at,
        )
        self.session.add(memory)
        self.session.flush()
        return memory

    async def _extract_async(
        self, text: str, *, history: list[dict[str, str]] | None = None
    ) -> list[ExtractedMemory]:
        if not self.provider.available:
            return []

        history = history or []
        system_prompt = (
            "提取当前用户消息明确陈述的本人学习事实，历史只用于指代和短回答消歧。"
            "不能重新提取历史事实，不能将助手的推测作为用户事实。evidence 必须原样摘自当前消息。"
            "逐条标明 subject=user/other/unclear、scope=persistent/task/hypothetical/unclear。"
            "朋友、同学的信息属于 other；本次荐书要求属于 task；假设、引用、举例不作为本人事实。"
            "只在明确时返回事实，否则返回空列表。未知不等于零基础。"
            "foundation 的 topic 是具体知识点；value_json 是含 level 的 JSON 对象，"
            "level 只能为 none/basic/intermediate/advanced/unknown。能力依据是用户自述，不是测评。"
            "例如：我没学过Python => Python/none；我想学Python仅表示 learning_goals，"
            "不能推断为 Python/none。回答‘没有’只有在前文明确询问本人单一知识点基础时才能提取。"
            "learning_goals/interests 的 value_json 是字符串数组；major/grade 为 JSON 字符串；"
            "数组使用原文中的知识点或目标短语，不扩展为用户未提及的领域或目标。"
            "difficulty_preference 是长期偏好，值为 beginner/progressive/intermediate/advanced。"
            "目标和兴趣的 operation：补充用 add，明确替换用 set，不再喜欢或放弃用 remove。"
            "混合表达逐项判断，例如‘帮朋友找书，我没学过Python’，只保留明确的本人事实。"
        )
        try:
            result = await self.provider.structured(
                [
                    {"role": "system", "content": system_prompt},
                    *history,
                    {"role": "user", "content": text},
                ],
                ProfileExtraction,
            )
            extracted: list[ExtractedMemory] = []
            positions: dict[tuple[str, str], int] = {}
            for fact in sorted(result.facts, key=lambda item: text.find(item.evidence)):
                value = validate_fact(fact, text, history)
                if value is not None:
                    identity = (value.category, value.key)
                    if isinstance(value.value, list):
                        previous = extracted[-1] if extracted else None
                        if previous and (previous.category, previous.key, previous.operation) == (
                            value.category,
                            value.key,
                            value.operation,
                        ):
                            extracted[-1] = ExtractedMemory(
                                value.category,
                                value.key,
                                list(dict.fromkeys([*previous.value, *value.value])),
                                min(previous.confidence, value.confidence),
                                value.operation,
                            )
                        else:
                            extracted.append(value)
                    elif identity in positions:
                        extracted[positions[identity]] = value
                    else:
                        positions[identity] = len(extracted)
                        extracted.append(value)
            return extracted
        except Exception:
            logger.warning("Profile fact extraction failed; no facts written", exc_info=True)
            return []
