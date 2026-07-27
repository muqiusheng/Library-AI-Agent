from uuid import UUID, uuid4

from sqlalchemy import desc, insert, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Book, BookTag, DataVersion, DataVersionStatus, ReviewStatus
from app.integrations.llm.deepseek import DeepSeekError, DeepSeekProvider
from app.schemas.tag_review import AITagOutput, AITagRunResult, TagReviewRead

_ENUM_VALUES = {
    "difficulty": {"beginner", "intermediate", "advanced"},
    "learning_stage": {"入门", "核心", "进阶", "实践"},
    "content_style": {"项目", "案例", "题解", "理论"},
}

_ENUM_ALIASES = {
    "difficulty": {
        "初级": "beginner",
        "入门": "beginner",
        "初学者": "beginner",
        "基础": "beginner",
        "中级": "intermediate",
        "中等": "intermediate",
        "高级": "advanced",
        "进阶": "advanced",
        "困难": "advanced",
    },
    "learning_stage": {
        "初学": "入门",
        "基础": "入门",
        "重点": "核心",
        "提高": "进阶",
        "高级": "进阶",
        "实战": "实践",
        "项目": "实践",
    },
    "content_style": {
        "实战": "项目",
        "项目制": "项目",
        "实例": "案例",
        "案例分析": "案例",
        "习题": "题解",
        "解题": "题解",
        "原理": "理论",
        "理论型": "理论",
    },
}


class AITaggingService:
    def __init__(self, session: Session, provider: DeepSeekProvider | None = None) -> None:
        self.session = session
        self.provider = provider or DeepSeekProvider()

    async def run(self, data_version_id: UUID | None, limit: int) -> AITagRunResult:
        if not self.provider.available:
            raise AppError(
                status_code=409, code="LLM_NOT_CONFIGURED", message="尚未配置大模型 API Key"
            )
        version_id = self._resolve_version(data_version_id)
        books = list(
            self.session.scalars(
                select(Book)
                .where(Book.data_version_id == version_id)
                .order_by(Book.id)
                .limit(limit)
            )
        )
        existing_ids = set(
            self.session.scalars(
                select(BookTag.book_id).where(
                    BookTag.book_id.in_([book.id for book in books]),
                    BookTag.source == "deepseek",
                )
            )
        )
        pending = [book for book in books if book.id not in existing_ids]
        created = tagged = 0
        for start in range(0, len(pending), 10):
            batch = pending[start : start + 10]
            proposals = await self._request_batch(batch)
            allowed_ids = {book.id for book in batch}
            returned_ids = {proposal.book_id for proposal in proposals.books}
            if not returned_ids.issubset(allowed_ids):
                raise AppError(
                    status_code=502, code="AI_TAG_UNKNOWN_BOOK", message="AI 返回了未知图书 ID"
                )
            rows = []
            for proposal in proposals.books:
                for tag in proposal.tags:
                    allowed_values = _ENUM_VALUES.get(tag.tag_type)
                    tag_value = _ENUM_ALIASES.get(tag.tag_type, {}).get(
                        tag.tag_value.strip(), tag.tag_value.strip()
                    )
                    if allowed_values is not None and tag_value not in allowed_values:
                        continue
                    rows.append(
                        {
                            "id": uuid4(),
                            "book_id": proposal.book_id,
                            "tag_type": tag.tag_type,
                            "tag_value": tag_value,
                            "confidence": tag.confidence,
                            "source": "deepseek",
                            "model_name": self.provider.settings.deepseek_chat_model,
                            "prompt_version": "ai-tag-v1",
                            "review_status": ReviewStatus.PENDING.value,
                            "reviewer_id": None,
                        }
                    )
                tagged += 1
            if rows:
                self.session.execute(insert(BookTag), rows)
                created += len(rows)
                self.session.commit()
        return AITagRunResult(
            requested_books=len(books),
            tagged_books=tagged,
            created_tags=created,
            cached_books=len(existing_ids),
        )

    async def _request_batch(self, books: list[Book]) -> AITagOutput:
        payload = [
            {
                "book_id": str(book.id),
                "title": book.title,
                "responsible_person": book.responsible_person,
                "publisher": book.publisher,
                "description": book.description,
            }
            for book in books
        ]
        try:
            return await self.provider.structured(
                [
                    {
                        "role": "user",
                        "content": (
                            "为以下图书生成主题、难度、学习阶段和内容风格标签。"
                            "只能使用输入中的 book_id。每本书应包含 topic、difficulty、"
                            "learning_stage、content_style；difficulty 只能是 beginner、"
                            "intermediate、advanced；learning_stage 只能是入门、核心、进阶、实践；"
                            "content_style 只能是项目、案例、题解、理论；不要创造其他枚举值。"
                            f"图书：{payload}"
                        ),
                    }
                ],
                AITagOutput,
            )
        except DeepSeekError as exc:
            raise AppError(status_code=502, code=exc.code, message=exc.message) from exc

    def _resolve_version(self, requested: UUID | None) -> UUID:
        if requested is not None:
            version = self.session.get(DataVersion, requested)
        else:
            version = self.session.scalar(
                select(DataVersion)
                .where(DataVersion.status == DataVersionStatus.PUBLISHED)
                .order_by(desc(DataVersion.published_at))
                .limit(1)
            )
        if version is None:
            raise AppError(status_code=404, code="DATA_VERSION_NOT_FOUND", message="数据版本不存在")
        return version.id


class TagReviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_pending(self, limit: int, offset: int) -> list[TagReviewRead]:
        rows = self.session.execute(
            select(BookTag, Book.title)
            .join(Book, Book.id == BookTag.book_id)
            .where(BookTag.review_status == ReviewStatus.PENDING)
            .order_by(desc(BookTag.created_at))
            .offset(offset)
            .limit(limit)
        ).all()
        return [self._read(tag, title) for tag, title in rows]

    def update(
        self,
        tag_id: UUID,
        reviewer_id: UUID,
        tag_type: str,
        tag_value: str,
        status: ReviewStatus,
    ) -> TagReviewRead:
        tag = self.session.get(BookTag, tag_id)
        if tag is None:
            raise AppError(status_code=404, code="TAG_NOT_FOUND", message="标签不存在")
        allowed = _ENUM_VALUES.get(tag_type)
        if allowed is not None and tag_value not in allowed:
            raise AppError(status_code=422, code="INVALID_TAG_ENUM", message="标签值不在允许范围内")
        tag.tag_type = tag_type
        tag.tag_value = tag_value
        tag.review_status = status
        tag.reviewer_id = reviewer_id
        self.session.commit()
        title = self.session.scalar(select(Book.title).where(Book.id == tag.book_id)) or ""
        return self._read(tag, title)

    def bulk_review(self, tag_ids: list[UUID], reviewer_id: UUID, status: ReviewStatus) -> int:
        tags = list(self.session.scalars(select(BookTag).where(BookTag.id.in_(tag_ids))))
        if len(tags) != len(set(tag_ids)):
            raise AppError(status_code=404, code="TAG_NOT_FOUND", message="批量审核包含未知标签")
        for tag in tags:
            tag.review_status = status
            tag.reviewer_id = reviewer_id
        self.session.commit()
        return len(tags)

    @staticmethod
    def _read(tag: BookTag, title: str) -> TagReviewRead:
        return TagReviewRead(
            id=tag.id,
            book_id=tag.book_id,
            book_title=title,
            tag_type=tag.tag_type,
            tag_value=tag.tag_value,
            confidence=tag.confidence,
            source=tag.source,
            model_name=tag.model_name,
            prompt_version=tag.prompt_version,
            review_status=tag.review_status,
            reviewer_id=tag.reviewer_id,
        )
