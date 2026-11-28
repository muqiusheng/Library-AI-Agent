from collections import Counter, defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.content_orientation import ORIENTATION_LABELS, parse_orientation
from app.db.models import Book, Holding, ImportBatch


def backfill_content_orientation(session: Session, version_id: UUID) -> dict:
    """Validate every copy before applying a version's confirmed dataset labels."""
    books = list(session.scalars(select(Book).where(Book.data_version_id == version_id)))
    values: dict[UUID, set[str]] = defaultdict(set)
    rows = session.execute(
        select(Holding.book_id, Holding.raw_payload)
        .join(Book, Book.id == Holding.book_id)
        .where(Book.data_version_id == version_id)
    )
    for book_id, payload in rows:
        value = parse_orientation((payload or {}).get("内容取向"))
        if value is not None:
            values[book_id].add(value)
    conflicts = [str(book_id) for book_id, labels in values.items() if len(labels) > 1]
    if conflicts:
        raise ValueError(f"同一图书的内容取向不一致，未回填：{', '.join(conflicts[:10])}")
    updated = 0
    for book in books:
        labels = values.get(book.id)
        value = next(iter(labels)) if labels else None
        if book.content_orientation != value:
            book.content_orientation = value
            updated += 1
    distribution = dict(
        Counter(ORIENTATION_LABELS.get(book.content_orientation, "未标注") for book in books)
    )
    for batch in session.scalars(
        select(ImportBatch).where(ImportBatch.data_version_id == version_id)
    ):
        batch.statistics = {**batch.statistics, "content_orientation_distribution": distribution}
    session.commit()
    return {
        "data_version_id": str(version_id),
        "books": len(books),
        "updated": updated,
        "content_orientation_distribution": distribution,
    }
