from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.models import (
    Book,
    BookUserStateValue,
    LearningPath,
    LearningPathBook,
    LearningPathStage,
    LearningPathStatus,
    RecommendationSet,
)
from app.schemas.learning_path import (
    LearningPathRead,
    LearningPathSummary,
    PathBookRead,
    PathStageRead,
)

_STAGES = (
    ("基础入门", "建立核心概念和必要基础", "1–2 周", "完成本阶段图书的核心章节"),
    ("核心进阶", "形成系统知识并完成配套练习", "2–3 周", "能够解释关键原理并完成练习"),
    ("项目实践", "通过案例把知识转化为实践能力", "2–4 周", "完成一个可展示的小型项目"),
)


class LearningPathService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_from_recommendation(
        self, user_id: UUID, set_id: UUID, title: str | None
    ) -> LearningPathRead:
        recommendation = self.session.scalar(
            select(RecommendationSet)
            .where(RecommendationSet.id == set_id, RecommendationSet.user_id == user_id)
            .options(selectinload(RecommendationSet.items))
        )
        if recommendation is None or not recommendation.items:
            raise AppError(
                status_code=404, code="RECOMMENDATION_NOT_FOUND", message="推荐结果不存在"
            )
        ordered_items = sorted(recommendation.items, key=lambda item: item.rank)
        path = LearningPath(
            user_id=user_id,
            conversation_id=recommendation.conversation_id,
            title=(title or f"{recommendation.query[:40]}学习路径").strip(),
            goal=recommendation.query,
            status=LearningPathStatus.DRAFT,
            progress=0,
        )
        self.session.add(path)
        self.session.flush()
        buckets = self._buckets(len(ordered_items))
        start = 0
        for position, (stage_info, size) in enumerate(zip(_STAGES, buckets, strict=True), start=1):
            stage_title, objective, duration, criteria = stage_info
            stage = LearningPathStage(
                path_id=path.id,
                position=position,
                title=stage_title,
                objective=objective,
                duration_text=duration,
                prerequisites=None if position == 1 else f"完成第 {position - 1} 阶段",
                completion_criteria=criteria,
            )
            self.session.add(stage)
            self.session.flush()
            for book_position, item in enumerate(ordered_items[start : start + size], start=1):
                self.session.add(
                    LearningPathBook(
                        stage_id=stage.id,
                        book_id=item.book_id,
                        position=book_position,
                        state=BookUserStateValue.WANT_TO_READ,
                    )
                )
            start += size
        self.session.commit()
        return self.get_owned(path.id, user_id)

    def list_for_user(self, user_id: UUID) -> list[LearningPathSummary]:
        paths = list(
            self.session.scalars(
                select(LearningPath)
                .where(LearningPath.user_id == user_id)
                .options(selectinload(LearningPath.stages).selectinload(LearningPathStage.books))
                .order_by(LearningPath.updated_at.desc())
            )
        )
        return [
            LearningPathSummary(
                id=path.id,
                title=path.title,
                goal=path.goal,
                status=path.status,
                progress=float(path.progress),
                stage_count=len(path.stages),
                book_count=sum(len(stage.books) for stage in path.stages),
                updated_at=path.updated_at,
            )
            for path in paths
        ]

    def get_owned(self, path_id: UUID, user_id: UUID) -> LearningPathRead:
        path = self.session.scalar(
            select(LearningPath)
            .where(LearningPath.id == path_id, LearningPath.user_id == user_id)
            .options(selectinload(LearningPath.stages).selectinload(LearningPathStage.books))
        )
        if path is None:
            raise AppError(
                status_code=404, code="LEARNING_PATH_NOT_FOUND", message="学习路径不存在"
            )
        book_ids = [book.book_id for stage in path.stages for book in stage.books]
        titles = dict(
            self.session.execute(
                select(Book.id, Book.title).where(Book.id.in_(book_ids))
            ).all()
        )
        return LearningPathRead(
            id=path.id,
            title=path.title,
            goal=path.goal,
            status=path.status,
            progress=float(path.progress),
            conversation_id=path.conversation_id,
            created_at=path.created_at,
            updated_at=path.updated_at,
            stages=[
                PathStageRead(
                    id=stage.id,
                    position=stage.position,
                    title=stage.title,
                    objective=stage.objective,
                    duration_text=stage.duration_text,
                    prerequisites=stage.prerequisites,
                    completion_criteria=stage.completion_criteria,
                    books=[
                        PathBookRead(
                            book_id=book.book_id,
                            title=titles.get(book.book_id, "馆藏图书"),
                            position=book.position,
                            state=book.state,
                        )
                        for book in sorted(stage.books, key=lambda value: value.position)
                    ],
                )
                for stage in sorted(path.stages, key=lambda value: value.position)
            ],
        )

    def update_status(
        self, path_id: UUID, user_id: UUID, status: LearningPathStatus
    ) -> LearningPathRead:
        path = self._model_owned(path_id, user_id)
        path.status = status
        if status == LearningPathStatus.COMPLETED:
            for stage in path.stages:
                for book in stage.books:
                    book.state = BookUserStateValue.COMPLETED
            path.progress = Decimal("100.00")
        self.session.commit()
        return self.get_owned(path_id, user_id)

    def update_book_state(
        self,
        path_id: UUID,
        book_id: UUID,
        user_id: UUID,
        state: BookUserStateValue,
    ) -> LearningPathRead:
        path = self._model_owned(path_id, user_id)
        matching = [
            book for stage in path.stages for book in stage.books if book.book_id == book_id
        ]
        if not matching:
            raise AppError(status_code=404, code="PATH_BOOK_NOT_FOUND", message="路径图书不存在")
        matching[0].state = state
        books = [book for stage in path.stages for book in stage.books]
        completed = sum(book.state == BookUserStateValue.COMPLETED for book in books)
        path.progress = Decimal(str(round(completed * 100 / len(books), 2)))
        if completed == len(books):
            path.status = LearningPathStatus.COMPLETED
        elif path.status in {LearningPathStatus.DRAFT, LearningPathStatus.COMPLETED}:
            path.status = LearningPathStatus.ACTIVE
        self.session.commit()
        return self.get_owned(path_id, user_id)

    def _model_owned(self, path_id: UUID, user_id: UUID) -> LearningPath:
        path = self.session.scalar(
            select(LearningPath)
            .where(LearningPath.id == path_id, LearningPath.user_id == user_id)
            .options(selectinload(LearningPath.stages).selectinload(LearningPathStage.books))
        )
        if path is None:
            raise AppError(
                status_code=404, code="LEARNING_PATH_NOT_FOUND", message="学习路径不存在"
            )
        return path

    @staticmethod
    def _buckets(total: int) -> tuple[int, int, int]:
        base, remainder = divmod(total, 3)
        values = [base, base, base]
        for index in range(remainder):
            values[index] += 1
        return values[0], values[1], values[2]
