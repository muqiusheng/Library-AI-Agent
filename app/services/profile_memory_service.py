import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import MemorySource, Message, ProfileMemory, User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileUpdate

_TEMPORARY_MARKERS = ("这次", "本次", "今天", "暂时", "当前会话", "只看", "先不要")
_TOPICS = ("Java", "Python", "数据库", "算法", "人工智能", "机器学习", "前端", "后端")


@dataclass(frozen=True)
class ExtractedMemory:
    category: str
    key: str
    value: dict[str, Any] | list[Any] | str | int | float | bool
    confidence: float


class ProfileMemoryService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ProfileRepository(session)

    def extract_from_message(self, user: User, message: Message) -> list[ProfileMemory]:
        extracted = self._extract(message.content)
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

    @staticmethod
    def _extract(text: str) -> list[ExtractedMemory]:
        if any(marker in text for marker in _TEMPORARY_MARKERS):
            return []
        values: list[ExtractedMemory] = []
        lowered = text.casefold()
        for topic in _TOPICS:
            normalized_topic = topic.casefold()
            if normalized_topic not in lowered:
                continue
            none_pattern = rf"(没学过|没有学过|零基础|从零学|不懂)\s*{re.escape(topic)}"
            reverse_none_pattern = rf"{re.escape(topic)}\s*(零基础|没学过|不会)"
            if re.search(none_pattern, text, re.IGNORECASE) or re.search(
                reverse_none_pattern, text, re.IGNORECASE
            ):
                values.append(
                    ExtractedMemory(
                        category="foundation",
                        key=f"topic:{normalized_topic}",
                        value={"topic": topic, "level": "none", "label": f"{topic} 零基础"},
                        confidence=0.96,
                    )
                )
            if re.search(rf"(喜欢|感兴趣|想深入)\s*{re.escape(topic)}", text, re.IGNORECASE):
                values.append(
                    ExtractedMemory(
                        category="interest",
                        key=f"topic:{normalized_topic}",
                        value={"topic": topic, "preference": "positive"},
                        confidence=0.9,
                    )
                )
        return values
