import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import MemorySource, Message, MessageRole, ProfileMemory, User
from app.integrations.llm.deepseek import DeepSeekProvider
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileUpdate
from app.services.profile_fact_extractor import ExtractedMemory, ProfileExtraction, validate_fact

logger = logging.getLogger(__name__)


class ProfileMemoryService:
    def __init__(self, session: Session, provider: DeepSeekProvider | None = None) -> None:
        self.session = session
        self.repository = ProfileRepository(session)
        self.provider = provider or DeepSeekProvider()

    async def extract_from_message(self, user: User, message: Message) -> list[ProfileMemory]:
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
            setattr(user.profile, field, value)
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
        self.session.commit()

    def edit_memory(self, user_id: UUID, memory_id: UUID, value: Any) -> ProfileMemory:
        existing = self.repository.get_owned_memory(memory_id, user_id)
        if existing is None:
            raise AppError(status_code=404, code="MEMORY_NOT_FOUND", message="画像记忆不存在")
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
        self.session.commit()
        return created

    def deactivate_memory(self, user_id: UUID, memory_id: UUID) -> None:
        memory = self.repository.get_owned_memory(memory_id, user_id)
        if memory is None:
            raise AppError(status_code=404, code="MEMORY_NOT_FOUND", message="画像记忆不存在")
        memory.is_active = False
        self.session.commit()

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
    ) -> ProfileMemory | None:
        existing = self.repository.active_for_key(user_id, category, key)
        if existing is not None:
            if protect_manual and existing.is_user_edited:
                return None
            if existing.value_json == value and existing.source == source:
                return None
            existing.is_active = False
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
            extracted: dict[tuple[str, str], ExtractedMemory] = {}
            positions: dict[tuple[str, str], int] = {}
            for fact in result.facts:
                value = validate_fact(fact, text, history)
                if value is not None:
                    identity = (value.category, value.key)
                    previous = extracted.get(identity)
                    position = text.find(fact.evidence)
                    if previous is not None and isinstance(value.value, list):
                        value = ExtractedMemory(
                            value.category,
                            value.key,
                            list(dict.fromkeys([*previous.value, *value.value])),
                            min(previous.confidence, value.confidence),
                        )
                    if (
                        previous is None
                        or isinstance(value.value, list)
                        or position >= positions[identity]
                    ):
                        extracted[identity] = value
                        positions[identity] = max(position, positions.get(identity, -1))
            return list(extracted.values())
        except Exception:
            logger.warning("Profile fact extraction failed; no facts written", exc_info=True)
            return []
