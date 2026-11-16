from datetime import timedelta
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.base import utc_now
from app.db.models import (
    Book,
    BookUserState,
    BookUserStateValue,
    DataVersion,
    DataVersionStatus,
    ReadingInterest,
    ReadingInterestEvent,
    User,
)


class ReadingInterestService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def statuses(self, user_id: UUID, ids: list[UUID]) -> list[dict]:
        now = utc_now()
        counts = dict(
            self.session.execute(
                select(
                    ReadingInterestEvent.book_id, func.count(distinct(ReadingInterestEvent.user_id))
                )
                .where(
                    ReadingInterestEvent.book_id.in_(ids),
                    ReadingInterestEvent.created_at >= now - timedelta(days=30),
                    ReadingInterestEvent.created_at <= now,
                )
                .group_by(ReadingInterestEvent.book_id)
            ).all()
        )
        interests = {
            row.book_id: row.active
            for row in self.session.scalars(
                select(ReadingInterest).where(
                    ReadingInterest.user_id == user_id, ReadingInterest.book_id.in_(ids)
                )
            )
        }
        states = {
            row.book_id: row.state
            for row in self.session.scalars(
                select(BookUserState).where(
                    BookUserState.user_id == user_id, BookUserState.book_id.in_(ids)
                )
            )
        }
        return [
            {
                "book_id": str(id_),
                "wanted": interests.get(id_, False),
                "state": states.get(id_, BookUserStateValue.NOT_STARTED),
                "heat_count": counts.get(id_, 0),
            }
            for id_ in ids
        ]

    def set_interest(self, user_id: UUID, book_id: UUID, wanted: bool) -> dict:
        # Serialize mutations per user, even when no interest row exists yet.
        self.session.execute(select(User.id).where(User.id == user_id).with_for_update())
        if self.session.get(Book, book_id) is None:
            raise AppError(status_code=404, code="BOOK_NOT_FOUND", message="图书不存在")
        value = self.session.get(ReadingInterest, (user_id, book_id))
        if value is None:
            value = ReadingInterest(user_id=user_id, book_id=book_id, active=False)
            self.session.add(value)
        if wanted and not value.active:
            value.added_at = utc_now()
            self.session.add(ReadingInterestEvent(user_id=user_id, book_id=book_id))
        value.active = wanted
        self.session.commit()
        return self.statuses(user_id, [book_id])[0]

    @staticmethod
    def book_data(book: Book) -> dict:
        return {
            "book_id": str(book.id),
            "title": book.title,
            "responsible_person": book.responsible_person,
            "isbn": book.isbn13 or book.isbn10,
            "holdings_count": len(book.holdings),
            "available_count": sum(
                h.book_status == "available" and h.circulation_status == "lendable"
                for h in book.holdings
            ),
        }

    def mine(self, user_id: UUID, page: int, page_size: int) -> dict:
        condition = (ReadingInterest.user_id == user_id, ReadingInterest.active.is_(True))
        total = (
            self.session.scalar(select(func.count()).select_from(ReadingInterest).where(*condition))
            or 0
        )
        rows = self.session.execute(
            select(Book, ReadingInterest.added_at)
            .join(ReadingInterest)
            .where(*condition)
            .options(selectinload(Book.holdings))
            .order_by(ReadingInterest.added_at.desc(), Book.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        statuses = {s["book_id"]: s for s in self.statuses(user_id, [b.id for b, _ in rows])}
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {**self.book_data(book), **statuses[str(book.id)], "added_at": added_at}
                for book, added_at in rows
            ],
        }

    def ranking(self, user_id: UUID, days: int, page: int, page_size: int) -> dict:
        if days not in (7, 30, 365):
            raise AppError(
                status_code=422, code="INVALID_PERIOD", message="请选择近7天、近30天或近一年"
            )
        now = utc_now()
        version = (
            select(DataVersion.id)
            .where(DataVersion.status == DataVersionStatus.PUBLISHED)
            .order_by(DataVersion.published_at.desc(), DataVersion.id)
            .limit(1)
            .scalar_subquery()
        )
        counts = (
            select(
                ReadingInterestEvent.book_id,
                func.count(distinct(ReadingInterestEvent.user_id)).label("heat_count"),
            )
            .join(Book, Book.id == ReadingInterestEvent.book_id)
            .where(
                ReadingInterestEvent.created_at >= now - timedelta(days=days),
                ReadingInterestEvent.created_at <= now,
                Book.data_version_id == version,
            )
            .group_by(ReadingInterestEvent.book_id)
            .subquery()
        )
        ranked = select(
            counts.c.book_id,
            counts.c.heat_count,
            func.rank().over(order_by=counts.c.heat_count.desc()).label("rank"),
        ).subquery()
        total = self.session.scalar(select(func.count()).select_from(ranked)) or 0
        rows = self.session.execute(
            select(Book, ranked.c.heat_count, ranked.c.rank)
            .join(ranked, Book.id == ranked.c.book_id)
            .options(selectinload(Book.holdings))
            .order_by(ranked.c.heat_count.desc(), Book.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        statuses = {s["book_id"]: s for s in self.statuses(user_id, [b.id for b, _, _ in rows])}
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "days": days,
            "items": [
                {
                    **self.book_data(book),
                    **statuses[str(book.id)],
                    "heat_count": count,
                    "rank": rank,
                }
                for book, count, rank in rows
            ],
        }
