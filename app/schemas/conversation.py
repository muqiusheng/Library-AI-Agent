from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import MessageRole, MessageType


class ConversationCreate(BaseModel):
    title: str = Field(
        default="新会话",
        min_length=1,
        max_length=200,
    )


class ConversationUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )
    archived: bool | None = None


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    only_available: bool = False


NeedField = Literal[
    "foundation",
    "basics_preference",
    "language_preference",
    "content_preference",
]


class LearningNeedState(BaseModel):
    topic: str | None = Field(default=None, max_length=4000)
    foundation: str | None = Field(default=None, max_length=1000)

    basics_preference: Literal[
        "first", "skip", "any"
    ] | None = None

    language_preference: Literal[
        "python", "non_python", "any", "not_applicable"
    ] | None = None

    content_preference: Literal[
        "theory", "practice", "balanced", "any"
    ] | None = None

    pending_fields: list[NeedField] = Field(default_factory=list)
    asked_fields: list[NeedField] = Field(default_factory=list)

    clarification_rounds: int = Field(default=0, ge=0, le=2)


class ConstraintUpdate(BaseModel):
    only_available: bool | None = None

    difficulty: str | None = Field(
        default=None,
        pattern="^(beginner|intermediate|advanced)$",
    )

    excluded_terms: list[str] | None = Field(
        default=None,
        max_length=20,
    )


class ConstraintRead(BaseModel):
    only_available: bool = False
    difficulty: str | None = None
    excluded_terms: list[str] = Field(default_factory=list)

    learning_need: LearningNeedState = Field(
        default_factory=LearningNeedState
    )


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    message_type: MessageType
    structured_payload: dict[str, Any] | None
    created_at: datetime