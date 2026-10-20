from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Book
from app.integrations.embeddings.bge import BGEEmbeddingProvider
from app.integrations.vector.chroma import ChromaVectorStore


class BookIndexService:
    def __init__(
        self,
        session: Session,
        store: ChromaVectorStore | None = None,
    ) -> None:
        self.session = session
        self.store = store or ChromaVectorStore(BGEEmbeddingProvider())

    def build(
        self, data_version_id: UUID, *, limit: int | None = None, batch_size: int = 128
    ) -> int:
        statement = (
            select(Book)
            .where(Book.data_version_id == data_version_id)
            .options(selectinload(Book.tags))
            .order_by(Book.id)
        )
        if limit:
            statement = statement.limit(limit)
        books = list(self.session.scalars(statement))
        indexed = 0
        for start in range(0, len(books), batch_size):
            batch = books[start : start + batch_size]
            documents = [self.document_for(book) for book in batch]
            metadata = [
                {
                    "data_version": str(data_version_id),
                    "title": book.title[:300],
                    **(
                        {"publication_year": book.publication_year} if book.publication_year else {}
                    ),
                }
                for book in batch
            ]
            indexed += self.store.upsert(
                data_version_id=data_version_id,
                book_ids=[book.id for book in batch],
                documents=documents,
                metadata=metadata,
            )
        return indexed

    @staticmethod
    def document_for(book: Book) -> str:
        grouped: dict[str, list[str]] = {}
        for tag in book.tags:
            grouped.setdefault(tag.tag_type, []).append(tag.tag_value)
        difficulty_stage = grouped.get("difficulty", []) + grouped.get("learning_stage", [])
        return "\n".join(
            (
                f"题名：{book.title}",
                f"责任者：{book.responsible_person or ''}",
                f"出版社与年份：{book.publisher or ''} {book.publication_year or ''}",
                f"简介：{book.description or ''}",
                f"主题：{'、'.join(grouped.get('topic', []))}",
                f"难度与阶段：{'、'.join(difficulty_stage)}",
                f"内容风格：{'、'.join(grouped.get('content_style', []))}",
            )
        )
