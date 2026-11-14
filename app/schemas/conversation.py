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

    # None：保持原条件
    # True：只看可借
    # False：取消可借限制
    only_available: bool | None = None


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

class RecommendationRetry(BaseModel):
    stage: Literal[
        "retrieving", "comparing", "generating"
    ] = "retrieving"
    excluded_profile_keys: list[str] | None = Field(
        default=None, max_length=40
    )
    only_available: bool | None = None


class ConversationTask(BaseModel):
    pending_profile_updates: list[dict[str, Any]] = Field(
        default_factory=list
    )
    pending_profile_request: str = ""
    topic: str = ""
    request: str = ""
    pending_question: str = ""
    excluded_book_ids: list[UUID] = Field(default_factory=list)
    focused_book_id: UUID | None = None


class TurnResolution(BaseModel):
    action: Literal[
        "recommend",
        "refine",
        "explain",
        "availability",
        "chat",
        "clarify",
    ]
    topic: str = ""
    standalone_query: str = ""
    new_topic: bool = False
    keep_constraints: bool = False
    target_rank: int | None = Field(default=None, ge=1)
    clarification: str = ""
    constraints: ConstraintUpdate = Field(
        default_factory=ConstraintUpdate
    )