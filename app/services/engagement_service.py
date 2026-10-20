from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import (
    BookUserState,
    BookUserStateValue,
    FeedbackType,
    RecommendationFeedback,
    RecommendationItem,
    RecommendationSet,
)
from app.schemas.engagement import FeedbackCreate


class EngagementService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_feedback(
        self, user_id: UUID, set_id: UUID, payload: FeedbackCreate
    ) -> RecommendationFeedback:
        recommendation = self.session.get(RecommendationSet, set_id)
        item = self.session.scalar(
            select(RecommendationItem).where(
                RecommendationItem.set_id == set_id,
                RecommendationItem.book_id == payload.book_id,
            )
        )
        if recommendation is None or recommendation.user_id != user_id or item is None:
            raise AppError(
                status_code=404, code="RECOMMENDATION_ITEM_NOT_FOUND", message="推荐图书不存在"
            )
        feedback = RecommendationFeedback(
            user_id=user_id,
            book_id=payload.book_id,
            set_id=set_id,
            type=payload.type,
            comment=payload.comment,
        )
        self.session.add(feedback)
        if payload.type == FeedbackType.READ:
            self.set_book_state(
                user_id, payload.book_id, BookUserStateValue.COMPLETED, commit=False
            )
        self.session.commit()
        return feedback

    def set_book_state(
        self,
        user_id: UUID,
        book_id: UUID,
        state: BookUserStateValue,
        *,
        commit: bool = True,
    ) -> BookUserState:
        value = self.session.get(BookUserState, (user_id, book_id))
        if value is None:
            value = BookUserState(user_id=user_id, book_id=book_id, state=state)
            self.session.add(value)
        else:
            value.state = state
        if commit:
            self.session.commit()
        return value
