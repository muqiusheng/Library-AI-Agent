from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
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

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.models.enums import DataVersionStatus, ReviewStatus, enum_values


class DataVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "data_versions"

    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    status: Mapped[DataVersionStatus] = mapped_column(
        Enum(DataVersionStatus, values_callable=enum_values, native_enum=False, length=20),
        default=DataVersionStatus.DRAFT,
        nullable=False,
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    books: Mapped[list["Book"]] = relationship(back_populates="data_version")


class Book(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "books"
    __table_args__ = (
        Index("ix_books_data_version_isbn13", "data_version_id", "isbn13"),
        Index("ix_books_data_version_title", "data_version_id", "normalized_title"),
        Index("ix_books_publication_year", "publication_year"),
        UniqueConstraint("data_version_id", "source_fingerprint"),
    )

    data_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_versions.id", ondelete="RESTRICT"), nullable=False
    )
    isbn10: Mapped[str | None] = mapped_column(String(10), index=True)
    isbn13: Mapped[str | None] = mapped_column(String(13), index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_title: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_person: Mapped[str | None] = mapped_column(Text)
    responsible_note: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(String(255))
    publication_year: Mapped[int | None] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    pages: Mapped[int | None] = mapped_column(Integer)
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    volume_issue: Mapped[str | None] = mapped_column(String(100))
    cover_url: Mapped[str | None] = mapped_column(Text)
    cover_category: Mapped[str | None] = mapped_column(String(50))
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    data_version: Mapped[DataVersion] = relationship(back_populates="books")
    holdings: Mapped[list["Holding"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )
    tags: Mapped[list["BookTag"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class Holding(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "holdings"
    __table_args__ = (
        Index("ix_holdings_book_status", "book_id", "book_status", "circulation_status"),
        Index("ix_holdings_collection_location", "collection_location"),
        UniqueConstraint("book_id", "source_row_no"),
    )

    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    source_row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    call_number: Mapped[str | None] = mapped_column(String(150))
    collection_location: Mapped[str | None] = mapped_column(String(255))
    current_location: Mapped[str | None] = mapped_column(String(255))
    shelf_number: Mapped[str | None] = mapped_column(String(100))
    book_status: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    circulation_status: Mapped[str] = mapped_column(String(50), nullable=False)
    acquired_at: Mapped[date | None] = mapped_column(Date)
    updated_source_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)

    book: Mapped[Book] = relationship(back_populates="holdings")


class BookTag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "book_tags"
    __table_args__ = (
        Index("ix_book_tags_type_value", "tag_type", "tag_value"),
        Index("ix_book_tags_review_status", "review_status"),
        UniqueConstraint("book_id", "tag_type", "tag_value", "source"),
    )

    book_id: Mapped[UUID] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"))
    tag_type: Mapped[str] = mapped_column(String(50), nullable=False)
    tag_value: Mapped[str] = mapped_column(String(150), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(50))
    review_status: Mapped[ReviewStatus] = mapped_column(
        Enum(ReviewStatus, values_callable=enum_values, native_enum=False, length=16),
        default=ReviewStatus.PENDING,
        nullable=False,
    )
    reviewer_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    book: Mapped[Book] = relationship(back_populates="tags")
