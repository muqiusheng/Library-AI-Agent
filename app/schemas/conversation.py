from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import MessageRole, MessageType


class ConversationCreate(BaseModel):
    title: str = Field(default="新会话", min_length=1, max_length=200)


class ConversationUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
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


class ConstraintUpdate(BaseModel):
    only_available: bool | None = None
    difficulty: str | None = Field(default=None, pattern="^(beginner|intermediate|advanced)$")
    excluded_terms: list[str] | None = Field(default=None, max_length=20)


class ConstraintRead(BaseModel):
    only_available: bool = False
    difficulty: str | None = None
    excluded_terms: list[str] = Field(default_factory=list)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: MessageRole
    content: str
    message_type: MessageType
    structured_payload: dict[str, Any] | None
    created_at: datetime
