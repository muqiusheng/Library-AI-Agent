from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_conversation_memory import memory_session as memory_session

from app.db.models import (
    Book,
    DataVersion,
    FeedbackType,
    Holding,
    RecommendationFeedback,
    RecommendationSet,
)
from app.integrations.library.local import LocalLibraryAdapter
from app.integrations.vector.chroma import VectorHit
from app.schemas.conversation import LearningNeedState
from app.services.need_clarification_service import NeedClarificationService, NeedExtraction
from app.services.recommendation_service import RecommendationService


def test_soft_preference_can_be_removed_without_losing_the_task():
    need = LearningNeedState(topic="数据分析", learning_goal="完成项目", preferred_terms=["pandas"])
    assert (
        "pandas" in RecommendationService._search_need("", {"learning_need": need.model_dump()})[1]
    )
    updated = NeedClarificationService._merge(need, NeedExtraction(preferred_terms=[]))
    topic, search = RecommendationService._search_need(
        "仅在馆可借", {"learning_need": updated.model_dump()}
    )
    assert topic == "数据分析"
    assert search == "数据分析 完成项目"


def test_excluding_java_keeps_books_that_mention_it_only_as_background():
    book = Book(title="Python 入门", description="无需 Java 基础")
    assert not RecommendationService._excluded_content(book, ["java"])
    book.description = "主要介绍 Java 编程和开发。"
    assert RecommendationService._excluded_content(book, ["java"])
    assert not RecommendationService._excluded_content(book, ["书名：java"])


@pytest.mark.asyncio
async def test_backfill_finds_lendable_book_beyond_first_fifty(memory_session):
    session, user, conversation = memory_session
    version = session.scalar(select(DataVersion))
    books = []
    for i in range(60):
        book = Book(
            id=uuid4(),
            data_version_id=version.id,
            title=f"海洋学 {i}",
            description="研究潮汐与海洋",
            normalized_title=f"海洋学 {i}",
            source_fingerprint=uuid4().hex,
        )
        book.holdings = [
            Holding(
                source_row_no=1,
                book_status="available",
                circulation_status="lendable" if i == 59 else "not_lendable",
            )
        ]
        books.append(book)
    session.add_all(books)
    session.commit()
    limits = []

    def search(query, *, limit, **kwargs):
        limits.append(limit)
        return books[:limit]

    service = RecommendationService(session)
    service.library.search_candidates = search
    result = await service.recommend(
        user=user, conversation_id=conversation.id, query="海洋学", only_available=True
    )
    assert limits == [50, 100]
    assert [card.book_id for card in result.items] == [books[-1].id]


def test_exact_title_survives_full_vector_channel(memory_session):
    session, _, _ = memory_session
    books = list(session.scalars(select(Book)))
    target = books[-1]
    hits = [VectorHit(book.id, 0.8) for book in books[:5]]
    adapter = LocalLibraryAdapter(session, SimpleNamespace(query=lambda **kwargs: hits))
    signals = {}
    results = adapter.search_candidates(
        "检索改写", topic=target.title, limit=5, semantic_scores=signals
    )
    assert results[0].id == target.id
    assert signals[books[0].id] == 0.8


@pytest.mark.asyncio
async def test_unrelated_inventory_does_not_fill_offline_results(memory_session):
    session, user, conversation = memory_session
    service = RecommendationService(session)
    result = await service.recommend(user=user, conversation_id=conversation.id, query="古埃及考古")
    assert result.items == []


@pytest.mark.asyncio
async def test_difficulty_ratings_affect_only_recent_matching_subjects(memory_session):
    session, user, conversation = memory_session
    service = RecommendationService(session)
    original = await service.recommend(user=user, conversation_id=conversation.id, query="Java")
    for card in original.items[:2]:
        session.add(
            RecommendationFeedback(
                user_id=user.id,
                book_id=card.book_id,
                set_id=original.id,
                type=FeedbackType.TOO_HARD,
            )
        )
    session.commit()

    async def difficulty(topic):
        result = await service.recommend(user=user, conversation_id=conversation.id, query=topic)
        return session.get(RecommendationSet, result.id).constraints_snapshot[
            "effective_difficulty"
        ]

    assert await difficulty("Java") == "beginner"
    assert await difficulty("Python") == "progressive"


def test_unknown_difficulty_is_reported_without_inventing_a_level(memory_session):
    session, user, _ = memory_session
    book = session.scalars(select(Book)).first()
    service = RecommendationService(session)
    card = service._card(service._score(book, book.title, user))
    assert card.difficulty == "unknown"
    assert "难度尚未确认" in card.reason
    book.description = "面向初学者，包含案例"
    assert service._card(service._score(book, book.title, user)).difficulty == "beginner"


def test_current_goal_outweighs_unrelated_profile_goal(memory_session):
    session, user, _ = memory_session
    service = RecommendationService(session)
    target = Book(title="数据分析", description="覆盖客户流失预测")
    alternative = Book(title="数据分析", description="课程项目实践")
    profile = {"learning_goals": ["课程项目"]}

    def goal(book):
        return service._score(
            book, "数据分析", user, profile=profile, purpose="用于客户流失预测"
        ).scores.goal

    assert goal(target) > goal(alternative)
