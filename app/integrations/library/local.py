import re
from uuid import UUID

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import AppError
from app.db.models import Book, DataVersion, DataVersionStatus
from app.integrations.embeddings.bge import BGEEmbeddingProvider
from app.integrations.vector.chroma import ChromaVectorStore


class LocalLibraryAdapter:
    def __init__(self, session: Session, vector_store: ChromaVectorStore | None = None) -> None:
        self.session = session
        self.vector_store = vector_store or ChromaVectorStore(BGEEmbeddingProvider())

    def published_version_id(self) -> UUID:
        value = self.session.scalar(
            select(DataVersion.id)
            .where(DataVersion.status == DataVersionStatus.PUBLISHED)
            .order_by(DataVersion.published_at.desc())
            .limit(1)
        )
        if value is None:
            raise AppError(
                status_code=503,
                code="LIBRARY_NOT_READY",
                message="馆藏数据尚未发布",
            )
        return value

    def get_books(self, ids: list[UUID]) -> list[Book]:
        if not ids:
            return []
        version_id = self.published_version_id()
        statement = (
            select(Book)
            .where(Book.id.in_(ids), Book.data_version_id == version_id)
            .options(selectinload(Book.holdings), selectinload(Book.tags))
        )
        by_id = {book.id: book for book in self.session.scalars(statement)}
        return [by_id[book_id] for book_id in ids if book_id in by_id]

    def get_book(self, book_id: UUID) -> Book | None:
        books = self.get_books([book_id])
        return books[0] if books else None

    def search_candidates(
        self,
        query: str,
        *,
        limit: int = 50,
        topic: str = "",
        semantic_scores: dict[UUID, float] | None = None,
    ) -> list[Book]:
        version_id = self.published_version_id()
        hits = self.vector_store.query(data_version_id=version_id, text=query, limit=limit)
        if semantic_scores is not None:
            semantic_scores.update((hit.book_id, hit.score) for hit in hits)

        exact_title = (topic or query).strip().casefold()
        exact = func.lower(Book.title) == exact_title
        tokens = self._tokens(f"{topic} {query}")[:8]
        title_hits = [Book.title.icontains(token, autoescape=True) for token in tokens]
        description_hits = [Book.description.icontains(token, autoescape=True) for token in tokens]
        title_score = sum((case((hit, 1), else_=0) for hit in title_hits), literal(0))
        statement = (
            select(Book.id, exact.label("exact"))
            .where(Book.data_version_id == version_id, or_(exact, *title_hits, *description_hits))
            .order_by(exact.desc(), title_score.desc(), Book.id)
            .limit(limit)
        )
        lexical = self.session.execute(statement).all()
        # Reciprocal rank fusion gives each retrieval channel an equal vote.
        ranks: dict[UUID, float] = {}
        for channel in ([row.id for row in lexical], [hit.book_id for hit in hits]):
            for rank, book_id in enumerate(channel, 1):
                ranks[book_id] = ranks.get(book_id, 0.0) + 1 / (60 + rank)
        exact_ids = {row.id for row in lexical if row.exact}
        ordered = sorted(ranks, key=lambda key: (key in exact_ids, ranks[key]), reverse=True)
        return self.get_books(ordered[:limit])

    @staticmethod
    def _tokens(query: str) -> list[str]:
        lowered = query.casefold()
        known = [
            word
            for word in (
                "java",
                "python",
                "数据库",
                "算法",
                "人工智能",
                "机器学习",
                "网络",
                "操作系统",
            )
            if word in lowered
        ]
        generic = re.findall(r"[a-z][a-z0-9+#.-]{1,20}|[\u4e00-\u9fff]{2,8}", lowered)
        return list(dict.fromkeys([*known, *generic]))
