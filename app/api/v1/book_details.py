from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.core.errors import AppError
from app.db.models import User
from app.db.session import get_db
from app.integrations.library.local import LocalLibraryAdapter
from app.schemas.common import ApiResponse, success_response
from app.services.reading_interest_service import ReadingInterestService

router = APIRouter(prefix="/api/v1/books", tags=["books"])


@router.get("/{book_id}", response_model=ApiResponse[dict])
def get_book_detail(
    book_id: UUID,
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict:
    book = LocalLibraryAdapter(session).get_book(book_id)
    if book is None:
        raise AppError(status_code=404, code="BOOK_NOT_FOUND", message="图书不存在")
    data = {
        "id": str(book.id),
        "title": book.title,
        "responsible_person": book.responsible_person,
        "isbn": book.isbn13 or book.isbn10,
        "publisher": book.publisher,
        "publication_year": book.publication_year,
        "description": book.description,
        "content_orientation": book.content_orientation,
        "pages": book.pages,
        "holdings": [
            {
                "id": str(holding.id),
                "call_number": holding.call_number,
                "collection_location": holding.collection_location,
                "current_location": holding.current_location,
                "shelf_number": holding.shelf_number,
                "book_status": holding.book_status,
                "circulation_status": holding.circulation_status,
            }
            for holding in book.holdings
        ],
    }
    data.update(ReadingInterestService(session).statuses(user.id, [book_id])[0])
    data["holdings_count"] = len(book.holdings)
    data["available_count"] = sum(
        h.book_status == "available" and h.circulation_status == "lendable" for h in book.holdings
    )
    return success_response(request.state.request_id, data)
