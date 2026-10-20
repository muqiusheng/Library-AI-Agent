import re
from uuid import UUID

from sqlalchemy import desc, or_, select
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
            .order_by(desc(DataVersion.published_at))
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

    def search_candidates(self, query: str, *, limit: int = 50) -> list[Book]:
        version_id = self.published_version_id()
        vector_hits = self.vector_store.query(data_version_id=version_id, text=query, limit=limit)
        vector_ids = [hit.book_id for hit in vector_hits]
        candidates = self.get_books(vector_ids)
        seen = {book.id for book in candidates}

        tokens = self._tokens(query)
        conditions = []
        for token in tokens[:8]:
            pattern = f"%{token}%"
            conditions.extend((Book.title.ilike(pattern), Book.description.ilike(pattern)))
        if conditions:
            statement = (
                select(Book)
                .where(Book.data_version_id == version_id, or_(*conditions))
                .options(selectinload(Book.holdings), selectinload(Book.tags))
                .limit(limit)
            )
            for book in self.session.scalars(statement).unique():
                if book.id not in seen:
                    candidates.append(book)
                    seen.add(book.id)

        if len(candidates) < 5:
            statement = (
                select(Book)
                .where(Book.data_version_id == version_id)
                .options(selectinload(Book.holdings), selectinload(Book.tags))
                .order_by(desc(Book.publication_year).nullslast(), Book.title)
                .limit(20)
            )
            for book in self.session.scalars(statement).unique():
                if book.id not in seen:
                    candidates.append(book)
                    seen.add(book.id)
                if len(candidates) >= limit:
                    break
        return candidates[:limit]

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
