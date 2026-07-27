from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import BookUserStateValue, FeedbackType


class FeedbackCreate(BaseModel):
    book_id: UUID
    type: FeedbackType
    comment: str | None = Field(default=None, max_length=500)


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    book_id: UUID
    set_id: UUID
    type: FeedbackType
    comment: str | None
    created_at: datetime


class BookStateUpdate(BaseModel):
    state: BookUserStateValue


class BookStateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    book_id: UUID
    state: BookUserStateValue
    created_at: datetime
    updated_at: datetime
