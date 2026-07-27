from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, SecretStr

from app.db.models import UserRole


class ManagedUserRead(BaseModel):
    id: UUID
    student_no: str
    display_name: str | None
    role: UserRole
    is_active: bool
    major: str | None
    created_at: datetime
    last_login_at: datetime | None


class AdminCreateRequest(BaseModel):
    student_no: str = Field(pattern=r"^[A-Za-z0-9_-]{4,64}$")
    display_name: str | None = Field(default=None, max_length=100)
    password: SecretStr = Field(min_length=8, max_length=16)


class ManagedUserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    role: Literal["student", "admin"] | None = None
    is_active: bool | None = None


class PasswordResetRequest(BaseModel):
    password: SecretStr = Field(min_length=8, max_length=16)


class RegistrationInviteStatus(BaseModel):
    configured: bool
    updated_at: datetime | None = None


class RegistrationInviteGenerated(RegistrationInviteStatus):
    code: str = Field(min_length=12, max_length=12)
