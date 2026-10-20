from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import DifficultyPreference, MemorySource
from app.schemas.auth import ProfileSummary


class ProfileUpdate(BaseModel):
    grade: str | None = Field(default=None, min_length=1, max_length=50)
    major: str | None = Field(default=None, min_length=1, max_length=150)
    foundation: str | None = Field(default=None, min_length=1, max_length=2000)
    learning_goals: list[str] | None = Field(default=None, min_length=1, max_length=20)
    interests: list[str] | None = Field(default=None, max_length=30)
    difficulty_preference: DifficultyPreference | None = None
    courses: list[str] | None = Field(default=None, max_length=30)
    read_books: list[str] | None = Field(default=None, max_length=100)
    career_direction: str | None = Field(default=None, max_length=255)


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    category: str
    key: str
    value_json: dict[str, Any] | list[Any] | str | int | float | bool
    source: MemorySource
    confidence: float
    is_active: bool
    is_user_edited: bool
    source_message_id: UUID | None
    created_at: datetime
    updated_at: datetime


class MemoryUpdate(BaseModel):
    value_json: dict[str, Any] | list[Any] | str | int | float | bool


class ProfileDetail(BaseModel):
    profile: ProfileSummary | None
    memories: list[MemoryRead]
