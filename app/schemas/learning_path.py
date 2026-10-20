from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import BookUserStateValue, LearningPathStatus


class LearningPathCreate(BaseModel):
    recommendation_set_id: UUID
    title: str | None = Field(default=None, max_length=200)


class PathBookRead(BaseModel):
    book_id: UUID
    title: str
    position: int
    state: BookUserStateValue


class PathStageRead(BaseModel):
    id: UUID
    position: int
    title: str
    objective: str
    duration_text: str
    prerequisites: str | None
    completion_criteria: str
    books: list[PathBookRead]


class LearningPathRead(BaseModel):
    id: UUID
    title: str
    goal: str
    status: LearningPathStatus
    progress: float
    conversation_id: UUID | None
    created_at: datetime
    updated_at: datetime
    stages: list[PathStageRead]


class LearningPathSummary(BaseModel):
    id: UUID
    title: str
    goal: str
    status: LearningPathStatus
    progress: float
    stage_count: int
    book_count: int
    updated_at: datetime


class LearningPathStatusUpdate(BaseModel):
    status: LearningPathStatus


class PathBookStateUpdate(BaseModel):
    state: BookUserStateValue
