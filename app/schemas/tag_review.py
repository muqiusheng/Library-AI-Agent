from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models.enums import ReviewStatus

TagType = Literal["topic", "difficulty", "learning_stage", "content_style"]


class AITagValue(BaseModel):
    tag_type: TagType
    tag_value: str = Field(min_length=1, max_length=150)
    confidence: float = Field(ge=0, le=1)


class AIBookTagProposal(BaseModel):
    book_id: UUID
    tags: list[AITagValue] = Field(min_length=1, max_length=8)


class AITagOutput(BaseModel):
    books: list[AIBookTagProposal] = Field(max_length=10)


class AITagRequest(BaseModel):
    data_version_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=500)


class AITagRunResult(BaseModel):
    requested_books: int
    tagged_books: int
    created_tags: int
    cached_books: int


class TagReviewRead(BaseModel):
    id: UUID
    book_id: UUID
    book_title: str
    tag_type: str
    tag_value: str
    confidence: float
    source: str
    model_name: str | None
    prompt_version: str | None
    review_status: ReviewStatus
    reviewer_id: UUID | None


class TagReviewUpdate(BaseModel):
    tag_type: TagType
    tag_value: str = Field(min_length=1, max_length=150)
    review_status: ReviewStatus = ReviewStatus.PENDING


class TagBulkReview(BaseModel):
    tag_ids: list[UUID] = Field(min_length=1, max_length=500)
    status: Literal[ReviewStatus.APPROVED, ReviewStatus.REJECTED]
