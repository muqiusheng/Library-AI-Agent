from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.models import (
    Book,
    BookUserState,
    BookUserStateValue,
    LearningPath,
    LearningPathStage,
    LearningPathStatus,
    User,
)


def recalculate_path(path: LearningPath) -> None:
    books = [book for stage in path.stages for book in stage.books]
    completed = sum(book.state == BookUserStateValue.COMPLETED for book in books)
    path.progress = Decimal(str(round(completed * 100 / len(books), 2))) if books else Decimal(0)
    if path.status == LearningPathStatus.ARCHIVED:
        return
    if books and completed == len(books):
        path.status = LearningPathStatus.COMPLETED
    elif path.status == LearningPathStatus.COMPLETED or any(
        book.state != BookUserStateValue.NOT_STARTED for book in books
    ):
        path.status = LearningPathStatus.ACTIVE


def set_reading_progress(
    session: Session,
    user_id: UUID,
    book_id: UUID,
    state: BookUserStateValue,
) -> BookUserState:
    # All reading mutations for an account use the same lock, including first inserts.
    session.execute(select(User.id).where(User.id == user_id).with_for_update())
    if session.get(Book, book_id) is None:
        raise AppError(status_code=404, code="BOOK_NOT_FOUND", message="图书不存在")
    value = session.get(BookUserState, (user_id, book_id))
    if value is None:
        value = BookUserState(user_id=user_id, book_id=book_id, state=state)
        session.add(value)
    else:
        value.state = state
    paths = session.scalars(
        select(LearningPath)
        .where(LearningPath.user_id == user_id)
        .options(selectinload(LearningPath.stages).selectinload(LearningPathStage.books))
    )
    for path in paths:
        matched = False
        for stage in path.stages:
            for book in stage.books:
                if book.book_id == book_id:
                    book.state = state
                    matched = True
        if matched:
            recalculate_path(path)
    session.flush()
    return value
