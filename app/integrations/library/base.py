from typing import Protocol
from uuid import UUID

from app.db.models import Book


class LibraryPort(Protocol):
    def published_version_id(self) -> UUID: ...

    def get_books(self, ids: list[UUID]) -> list[Book]: ...

    def search_candidates(self, query: str, *, limit: int = 50) -> list[Book]: ...

    def get_book(self, book_id: UUID) -> Book | None: ...
