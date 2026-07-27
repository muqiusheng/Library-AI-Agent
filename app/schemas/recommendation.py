from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class HoldingCard(BaseModel):
    id: UUID
    call_number: str | None
    collection_location: str | None
    current_location: str | None
    shelf_number: str | None
    book_status: str
    circulation_status: str


class ScoreBreakdown(BaseModel):
    goal: float
    difficulty: float
    major: float
    interest: float
    semantic: float
    availability: float


class RecommendationCard(BaseModel):
    book_id: UUID
    title: str
    responsible_person: str | None
    isbn: str | None
    publisher: str | None
    publication_year: int | None
    description: str | None
    topics: list[str]
    difficulty: str
    learning_stage: str
    total_score: float
    scores: ScoreBreakdown
    reason: str
    holdings_count: int
    available_count: int
    holdings: list[HoldingCard]


class RecommendationSetRead(BaseModel):
    id: UUID
    query: str
    summary: str
    created_at: datetime
    items: list[RecommendationCard]


class RefineRequest(BaseModel):
    instruction: str
    only_available: bool | None = None
