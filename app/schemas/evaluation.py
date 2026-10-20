from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvaluationCreate(BaseModel):
    tester_code: str = Field(pattern=r"^[A-Za-z0-9_-]{4,64}$")
    profile_scenario: str = Field(min_length=1, max_length=100)
    recommendation_set_id: UUID
    relevance_score: int = Field(ge=1, le=5)
    difficulty_score: int = Field(ge=1, le=5)
    reason_score: int = Field(ge=1, le=5)
    holding_score: int = Field(ge=1, le=5)
    satisfaction_score: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=1000)


class EvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tester_code: str
    profile_scenario: str
    recommendation_set_id: UUID
    relevance_score: int
    difficulty_score: int
    reason_score: int
    holding_score: int
    satisfaction_score: int
    notes: str | None
    created_at: datetime


class EvaluationAverages(BaseModel):
    relevance: float
    difficulty: float
    reason: float
    holding: float
    satisfaction: float


class EvaluationSummary(BaseModel):
    sample_size: int
    averages: EvaluationAverages
    satisfaction_distribution: dict[int, int]
    scenario_counts: dict[str, int]
