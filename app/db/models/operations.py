from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, utc_now
from app.db.models.enums import ImportStatus, IssueStatus, ReservationStatus, enum_values


class Reservation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (Index("ix_reservations_user_status", "user_id", "status"),)

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    holding_id: Mapped[UUID] = mapped_column(ForeignKey("holdings.id", ondelete="RESTRICT"))
    status: Mapped[ReservationStatus] = mapped_column(
        Enum(ReservationStatus, values_callable=enum_values, native_enum=False, length=16),
        default=ReservationStatus.ACTIVE,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Notification(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_read_created", "user_id", "read_at", "created_at"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )


class ImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (Index("ix_import_batches_status_created", "status", "created_at"),)

    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        Enum(ImportStatus, values_callable=enum_values, native_enum=False, length=16),
        default=ImportStatus.PENDING,
        nullable=False,
    )
    stage: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0, nullable=False)
    data_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("data_versions.id", ondelete="SET NULL")
    )
    statistics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ImportIssue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "import_issues"
    __table_args__ = (Index("ix_import_issues_batch_status", "batch_id", "status"),)

    batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE")
    )
    row_no: Mapped[int | None] = mapped_column(Integer)
    field_name: Mapped[str | None] = mapped_column(String(100))
    issue_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus, values_callable=enum_values, native_enum=False, length=16),
        default=IssueStatus.OPEN,
        nullable=False,
    )


class EvaluationRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_records"
    __table_args__ = (
        CheckConstraint("relevance_score BETWEEN 1 AND 5", name="relevance_score_range"),
        CheckConstraint("difficulty_score BETWEEN 1 AND 5", name="difficulty_score_range"),
        CheckConstraint("reason_score BETWEEN 1 AND 5", name="reason_score_range"),
        CheckConstraint("holding_score BETWEEN 1 AND 5", name="holding_score_range"),
        CheckConstraint("satisfaction_score BETWEEN 1 AND 5", name="satisfaction_score_range"),
        UniqueConstraint("tester_code", "recommendation_set_id"),
    )

    tester_code: Mapped[str] = mapped_column(String(64), nullable=False)
    profile_scenario: Mapped[str] = mapped_column(String(100), nullable=False)
    recommendation_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("recommendation_sets.id", ondelete="CASCADE")
    )
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty_score: Mapped[int] = mapped_column(Integer, nullable=False)
    reason_score: Mapped[int] = mapped_column(Integer, nullable=False)
    holding_score: Mapped[int] = mapped_column(Integer, nullable=False)
    satisfaction_score: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class SystemSetting(TimestampMixin, Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value_json: Mapped[dict[str, Any] | list[Any] | str | int | float | bool] = mapped_column(
        JSONB, nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text)
    updated_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
