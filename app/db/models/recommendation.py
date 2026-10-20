from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.db.models.enums import (
    BookUserStateValue,
    FeedbackType,
    LearningPathStatus,
    enum_values,
)


class RecommendationSet(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendation_sets"
    __table_args__ = (Index("ix_recommendation_sets_user_created", "user_id", "created_at"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    constraints_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    items: Mapped[list["RecommendationItem"]] = relationship(
        back_populates="recommendation_set",
        cascade="all, delete-orphan",
        order_by="RecommendationItem.rank",
    )


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"
    __table_args__ = (
        CheckConstraint("rank >= 1", name="rank_positive"),
        CheckConstraint("total_score >= 0 AND total_score <= 100", name="total_score_range"),
        UniqueConstraint("set_id", "rank"),
    )

    set_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_sets.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", ondelete="RESTRICT"), primary_key=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    total_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    goal_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    difficulty_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    major_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    interest_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    semantic_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    availability_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    reason_source: Mapped[str] = mapped_column(String(30), nullable=False)

    recommendation_set: Mapped[RecommendationSet] = relationship(back_populates="items")


class BookUserState(TimestampMixin, Base):
    __tablename__ = "book_user_states"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[BookUserStateValue] = mapped_column(
        Enum(BookUserStateValue, values_callable=enum_values, native_enum=False, length=20),
        nullable=False,
    )


class RecommendationFeedback(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "recommendation_feedback"
    __table_args__ = (Index("ix_recommendation_feedback_user_book", "user_id", "book_id"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    set_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_sets.id", ondelete="CASCADE")
    )
    type: Mapped[FeedbackType] = mapped_column(
        Enum(FeedbackType, values_callable=enum_values, native_enum=False, length=20),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class LearningPath(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        CheckConstraint("progress >= 0 AND progress <= 100", name="progress_range"),
        Index("ix_learning_paths_user_updated", "user_id", "updated_at"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    conversation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LearningPathStatus] = mapped_column(
        Enum(LearningPathStatus, values_callable=enum_values, native_enum=False, length=16),
        default=LearningPathStatus.DRAFT,
        nullable=False,
    )
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)

    stages: Mapped[list["LearningPathStage"]] = relationship(
        back_populates="path", cascade="all, delete-orphan", order_by="LearningPathStage.position"
    )


class LearningPathStage(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "learning_path_stages"
    __table_args__ = (
        CheckConstraint("position >= 1", name="position_positive"),
        UniqueConstraint("path_id", "position"),
    )

    path_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    duration_text: Mapped[str] = mapped_column(String(100), nullable=False)
    prerequisites: Mapped[str | None] = mapped_column(Text)
    completion_criteria: Mapped[str] = mapped_column(Text, nullable=False)

    path: Mapped[LearningPath] = relationship(back_populates="stages")
    books: Mapped[list["LearningPathBook"]] = relationship(
        back_populates="stage", cascade="all, delete-orphan", order_by="LearningPathBook.position"
    )


class LearningPathBook(Base):
    __tablename__ = "learning_path_books"
    __table_args__ = (
        CheckConstraint("position >= 1", name="position_positive"),
        UniqueConstraint("stage_id", "position"),
    )

    stage_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_path_stages.id", ondelete="CASCADE"), primary_key=True
    )
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", ondelete="RESTRICT"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[BookUserStateValue] = mapped_column(
        Enum(BookUserStateValue, values_callable=enum_values, native_enum=False, length=20),
        default=BookUserStateValue.WANT_TO_READ,
        nullable=False,
    )

    stage: Mapped[LearningPathStage] = relationship(back_populates="books")
