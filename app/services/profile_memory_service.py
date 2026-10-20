import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import MemorySource, Message, ProfileMemory, User
from app.integrations.llm.deepseek import DeepSeekError, DeepSeekProvider
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import ProfileUpdate

class ProfileFact(BaseModel):
    category: str = Field(description="Must be 'foundation', 'learning_goals', 'interests', 'difficulty_preference', 'major', or 'grade'")
    key: str = Field(description="A unique key, e.g. 'topic:机器学习'")
    value_json: str = Field(description="The extracted value serialized as a JSON string. For foundation, e.g. '{\"topic\": \"机器学习\", \"level\": \"none\", \"label\": \"零基础\"}'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")

class ProfileExtraction(BaseModel):
    facts: list[ProfileFact]



@dataclass(frozen=True)
class ExtractedMemory:
    category: str
    key: str
    value: dict[str, Any] | list[Any] | str | int | float | bool
    confidence: float

class ProfileMemoryService:
    def __init__(self, session: Session, provider: DeepSeekProvider | None = None) -> None:
        self.session = session
        self.repository = ProfileRepository(session)
        self.provider = provider or DeepSeekProvider()

    async def extract_from_message(self, user: User, message: Message) -> list[ProfileMemory]:
        extracted = await self._extract_async(message.content)
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

    async def _extract_async(self, text: str) -> list[ExtractedMemory]:
        if not self.provider.available:
            return []
            
        system_prompt = (
            "Analyze the user's message and extract any facts about their learning profile. "
            "Categories can be 'foundation' (what they already know or don't know, e.g., '懂机器学习', '没学过Python'), "
            "'learning_goals' (what they want to learn, e.g., '想学Agent', '考研'), "
            "'interests' (topics they like), 'difficulty_preference' (beginner/progressive/intermediate/advanced), "
            "'major' (their university major), or 'grade' (their year/grade). "
            "Return an empty list if no clear facts are found. "
            "For 'foundation', include level ('none', 'basic', 'intermediate', 'advanced')."
        )
        try:
            result = await self.provider.structured(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                ProfileExtraction
            )
            extracted = []
            for fact in result.facts:
                try:
                    parsed_value = json.loads(fact.value_json)
                except Exception:
                    parsed_value = fact.value_json
                extracted.append(
                    ExtractedMemory(
                        category=fact.category,
                        key=fact.key,
                        value=parsed_value,
                        confidence=fact.confidence
                    )
                )
            return extracted
        except Exception:
            return []
