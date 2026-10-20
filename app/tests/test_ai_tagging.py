from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Book, BookTag, DataVersion, DataVersionStatus
from app.db.session import engine
from app.schemas.tag_review import AIBookTagProposal, AITagOutput, AITagValue
from app.services.ai_tagging_service import AITaggingService


class FakeTagProvider:
    available = True
    settings = SimpleNamespace(deepseek_chat_model="test-deepseek")

    def __init__(self, output: AITagOutput) -> None:
        self.output = output
        self.calls = 0

    async def structured(self, _messages, _schema):
        self.calls += 1
        return self.output


@pytest.fixture
def tagging_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _published_book(session: Session) -> tuple[DataVersion, Book]:
    version = session.scalar(
        select(DataVersion)
        .where(DataVersion.status == DataVersionStatus.PUBLISHED)
        .order_by(DataVersion.published_at.desc())
        .limit(1)
    )
    assert version is not None
    book = session.scalar(
        select(Book)
        .where(Book.data_version_id == version.id)
        .order_by(Book.id)
        .limit(1)
    )
    assert book is not None
    session.execute(
        delete(BookTag).where(BookTag.book_id == book.id, BookTag.source == "deepseek")
    )
    session.commit()
    return version, book


@pytest.mark.asyncio
async def test_ai_tags_are_cached_per_book_content(tagging_session: Session) -> None:
    version, book = _published_book(tagging_session)
    provider = FakeTagProvider(
        AITagOutput(
            books=[
                AIBookTagProposal(
                    book_id=book.id,
                    tags=[AITagValue(tag_type="topic", tag_value="Java", confidence=0.91)],
                )
            ]
        )
    )
    service = AITaggingService(tagging_session, provider=provider)
    first = await service.run(version.id, 1)
    second = await service.run(version.id, 1)

    assert first.created_tags == 1
    assert second.cached_books == 1
    assert second.created_tags == 0
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_ai_tagging_rejects_unknown_book_id(tagging_session: Session) -> None:
    version, _book = _published_book(tagging_session)
    provider = FakeTagProvider(
        AITagOutput(
            books=[
                AIBookTagProposal(
                    book_id=uuid4(),
                    tags=[AITagValue(tag_type="topic", tag_value="未知", confidence=0.8)],
                )
            ]
        )
    )
    with pytest.raises(AppError) as error:
        await AITaggingService(tagging_session, provider=provider).run(version.id, 1)
    assert error.value.code == "AI_TAG_UNKNOWN_BOOK"


@pytest.mark.asyncio
async def test_ai_tagging_normalizes_enum_aliases_and_skips_unknown_values(
    tagging_session: Session,
) -> None:
    version, book = _published_book(tagging_session)
    provider = FakeTagProvider(
        AITagOutput(
            books=[
                AIBookTagProposal(
                    book_id=book.id,
                    tags=[
                        AITagValue(tag_type="difficulty", tag_value="初级", confidence=0.9),
                        AITagValue(tag_type="content_style", tag_value="实战", confidence=0.8),
                        AITagValue(tag_type="learning_stage", tag_value="未知阶段", confidence=0.7),
                    ],
                )
            ]
        )
    )

    result = await AITaggingService(tagging_session, provider=provider).run(version.id, 1)
    values = {
        (tag.tag_type, tag.tag_value)
        for tag in tagging_session.scalars(select(BookTag).where(BookTag.book_id == book.id))
    }

    assert result.created_tags == 2
    assert ("difficulty", "beginner") in values
    assert ("content_style", "项目") in values
