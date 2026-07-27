from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr

from app.db.models.enums import DifficultyPreference, UserRole


class ProfileRegistration(BaseModel):
    grade: str = Field(min_length=1, max_length=50)
    major: str = Field(min_length=1, max_length=150)
    foundation: str = Field(min_length=1, max_length=2000)
    learning_goals: list[str] = Field(min_length=1, max_length=20)
    interests: list[str] = Field(default_factory=list, max_length=30)
    difficulty_preference: DifficultyPreference = DifficultyPreference.PROGRESSIVE
    courses: list[str] = Field(default_factory=list, max_length=30)
    read_books: list[str] = Field(default_factory=list, max_length=100)
    career_direction: str | None = Field(default=None, max_length=255)


class RegisterRequest(BaseModel):
    student_no: str = Field(pattern=r"^[A-Za-z0-9_-]{4,64}$")
    password: SecretStr = Field(min_length=8, max_length=16)
    display_name: str | None = Field(default=None, max_length=100)
    registration_code: SecretStr | None = Field(default=None, min_length=8, max_length=128)
    profile: ProfileRegistration


class LoginRequest(BaseModel):
    student_no: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=128)


class ProfileSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grade: str
    major: str
    foundation: str
    learning_goals: list[str]
    interests: list[str]
    difficulty_preference: DifficultyPreference
    courses: list[str]
    read_books: list[str]
    career_direction: str | None


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    student_no: str
    display_name: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    profile: ProfileSummary | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserSummary


class LogoutResponse(BaseModel):
    logged_out: bool = True
