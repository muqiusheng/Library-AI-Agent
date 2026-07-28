from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import DifficultyPreference, MemorySource, UserRole, enum_values


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    student_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, values_callable=enum_values, native_enum=False, length=16),
        default=UserRole.STUDENT,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_identity_id: Mapped[str | None] = mapped_column(String(255), unique=True)

    profile: Mapped["UserProfile | None"] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    memories: Mapped[list["ProfileMemory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    grade: Mapped[str] = mapped_column(String(50), nullable=False)
    major: Mapped[str] = mapped_column(String(150), nullable=False)
    foundation: Mapped[str] = mapped_column(Text, nullable=False)
    learning_goals: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    interests: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    difficulty_preference: Mapped[DifficultyPreference] = mapped_column(
        Enum(DifficultyPreference, values_callable=enum_values, native_enum=False, length=20),
        default=DifficultyPreference.PROGRESSIVE,
        nullable=False,
    )
    courses: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    read_books: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False)
    career_direction: Mapped[str | None] = mapped_column(String(255))
    profile_summary: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User] = relationship(back_populates="profile")


class ProfileMemory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "profile_memories"
    __table_args__ = (
        Index("ix_profile_memories_user_active", "user_id", "is_active"),
        Index("ix_profile_memories_user_key", "user_id", "category", "key"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value_json: Mapped[dict[str, Any] | list[Any] | str | int | float | bool] = mapped_column(
        JSONB, nullable=False
    )
    source: Mapped[MemorySource] = mapped_column(
        Enum(MemorySource, values_callable=enum_values, native_enum=False, length=20),
        nullable=False,
    )
    source_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_user_edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped[User] = relationship(back_populates="memories")
