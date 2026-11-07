import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select
from test_conversation_memory import memory_session as memory_session

from app.db.models import Book
from app.integrations.llm.deepseek import DeepSeekError
from app.schemas.recommendation import ScoreBreakdown
from app.services.recommendation_service import (
    RecommendationService,
    RerankItem,
    RerankOutput,
    ScoredBook,
)


def candidate(description, score=80):
    return ScoredBook(
        book=Book(id=uuid4(), title="机器学习教材", description=description),
        scores=ScoreBreakdown(
            goal=score,
            difficulty=score,
            major=score,
            interest=score,
            semantic=score,
            availability=0,
        ),
        total=score,
        reason="初筛模板理由",
    )


def service_for(provider):
    return RecommendationService(
        SimpleNamespace(),
        library=SimpleNamespace(),
        llm=provider,
    )


@pytest.mark.asyncio
async def test_rerank_reads_descriptions_and_applies_model_order_and_reasons():
    theory = candidate("介绍机器学习理论和数学推导。", score=95)
    practice = candidate("使用 Python 完成分类项目，讲解数据处理和模型评估。", score=70)
    unknown = candidate(None)
    blank = candidate("")
    reason = "简介包含分类项目与模型评估，符合动手实践目标；先修要求尚无法确认。"
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=RerankOutput(
                items=[
                    RerankItem(book_id=practice.book.id, rank=1, reason=reason),
                    RerankItem(book_id=theory.book.id, rank=2, reason="简介侧重理论，可作补充。"),
                ]
            )
        ),
    )
    profile = {"abilities": {"python": {"level": "basic"}}}
    result = await service_for(provider)._rerank(
        "我会 Python，想通过项目学机器学习",
        [theory, practice, unknown, blank],
        profile=profile,
    )

    messages, schema = provider.structured.call_args.args
    payload = json.loads(messages[1]["content"].split("候选：", 1)[1])
    assert [item["description"] for item in payload] == [
        theory.book.description,
        practice.book.description,
        None,
        "",
    ]
    assert all("fit" not in item for item in payload)
    assert all(item["available_count"] == 0 for item in payload)
    assert json.dumps(profile, ensure_ascii=False) in messages[1]["content"]
    assert schema is RerankOutput
    assert result == [practice, theory]
    assert result[0].reason == reason
    assert result[0].reason_source == "llm"
    assert result[0].total == 70


@pytest.mark.asyncio
@pytest.mark.parametrize("select_one", [True, False])
async def test_model_can_select_fewer_books_without_reintroducing_rejected_candidates(select_one):
    books = [candidate("Python 项目实践。"), candidate("Java 语法。")]
    selected = [RerankItem(book_id=books[0].book.id, rank=1, reason="简介包含 Python 项目。")]
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(return_value=RerankOutput(items=selected if select_one else [])),
    )

    result = await service_for(provider)._rerank("Python 项目", books)

    assert result == (books[:1] if select_one else [])


@pytest.mark.asyncio
async def test_rerank_only_returns_unique_candidate_ids():
    books = [candidate("Python 项目实践。"), candidate("Python 理论。")]
    selected = RerankItem(book_id=books[1].book.id, rank=1, reason="简介介绍 Python 理论。")
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=RerankOutput(
                items=[
                    RerankItem(book_id=uuid4(), rank=1, reason="候选外的图书"),
                    selected,
                    selected,
                ]
            )
        ),
    )

    assert await service_for(provider)._rerank("Python", books) == [books[1]]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["offline", "error", "unknown_ids", "no_candidates"])
async def test_rerank_preserves_rule_fallback_when_model_is_unusable(mode):
    books = [] if mode == "no_candidates" else [candidate("Python 理论。"), candidate(None)]
    provider = SimpleNamespace(
        available=mode != "offline",
        structured=AsyncMock(
            return_value=RerankOutput(
                items=[
                    RerankItem(book_id=uuid4(), rank=1, reason="候选外的图书"),
                ]
            )
        ),
    )
    if mode == "error":
        provider.structured.side_effect = DeepSeekError("INVALID_STRUCTURE", "模型返回无效")

    result = await service_for(provider)._rerank("Python", books)

    assert result == books
    assert all(item.reason == "初筛模板理由" for item in result)
    assert all(item.reason_source == "rule" for item in result)
    if mode in {"offline", "no_candidates"}:
        provider.structured.assert_not_called()


@pytest.mark.asyncio
async def test_rerank_can_rank_all_ten_candidates():
    books = [candidate(f"Python 项目 {i}") for i in range(10)]
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=RerankOutput(
                items=[
                    RerankItem(book_id=item.book.id, rank=i, reason="简介包含项目实践。")
                    for i, item in enumerate(reversed(books), start=1)
                ]
            )
        ),
    )

    assert await service_for(provider)._rerank("Python 项目", books) == list(reversed(books))


@pytest.mark.asyncio
async def test_description_based_selection_persists_and_summary_receives_selected_evidence(
    memory_session,
):
    session, user, conversation = memory_session
    books = list(session.scalars(select(Book).where(Book.title.like("Python%"))))[:3]
    books[0].description = "讲解 Python 理论。"
    books[1].description = "使用 Python 完成分类项目，包含数据处理和模型评估。"
    books[2].description = "Python 分类项目，但目前不可借。"
    books[2].holdings[0].circulation_status = "not_lendable"
    reason = "简介包含分类项目、数据处理和模型评估，符合项目学习目标；先修要求未说明。"
    captured = []

    class Model:
        available = True
        settings = SimpleNamespace(deepseek_chat_model="test-description-rerank")

        async def structured(self, messages, schema):
            if schema.__name__ == "EnrichedQuery":
                return schema(keywords="Python 项目")
            captured.append(messages)
            return schema(items=[{"book_id": books[1].id, "rank": 1, "reason": reason}])

        async def stream_chat(self, messages, **kwargs):
            captured.append(messages)
            yield "为你选择了 1 本包含项目实践的图书，先修要求尚无法确认。"

    service = RecommendationService(
        session,
        library=SimpleNamespace(
            search_candidates=lambda *args, **kwargs: books,
            get_books=lambda ids: [book for book in books if book.id in ids],
        ),
        llm=Model(),
    )
    result = await service.recommend(
        user=user,
        conversation_id=conversation.id,
        query="Python 项目",
        only_available=True,
    )

    payload = json.loads(captured[0][1]["content"].split("候选：", 1)[1])
    assert {item["book_id"] for item in payload} == {str(book.id) for book in books[:2]}
    assert all(item["available_count"] > 0 for item in payload)
    assert [item.book_id for item in result.items] == [books[1].id]
    stored = service.get_set(result.id, user.id)
    assert [item.book_id for item in stored.items] == [books[1].id]
    assert stored.items[0].reason == reason

    summary = "".join([chunk async for chunk in service.stream_summary(result, user)])
    assert "1 本" in summary
    summary_books = json.loads(
        captured[1][1]["content"].split("已选图书资料：", 1)[1].split("\n总计", 1)[0]
    )
    assert summary_books == [
        {
            "title": books[1].title,
            "description": books[1].description,
            "reason": reason,
            "available_count": 1,
        }
    ]


@pytest.mark.asyncio
async def test_empty_selection_persists_and_uses_clear_summary_without_another_model_call(
    memory_session,
):
    session, user, conversation = memory_session
    books = list(session.scalars(select(Book).where(Book.title.like("Python%"))))[:2]
    provider = SimpleNamespace(
        available=True,
        settings=SimpleNamespace(deepseek_chat_model="test-description-rerank"),
        structured=AsyncMock(
            side_effect=lambda messages, schema: (
                schema(keywords="Python")
                if schema.__name__ == "EnrichedQuery"
                else schema(items=[])
            )
        ),
        stream_chat=AsyncMock(),
    )
    service = RecommendationService(
        session,
        library=SimpleNamespace(
            search_candidates=lambda *args, **kwargs: books,
            get_books=lambda ids: [book for book in books if book.id in ids],
        ),
        llm=provider,
    )

    result = await service.recommend(
        user=user,
        conversation_id=conversation.id,
        query="Python 项目",
    )

    assert result.items == []
    assert service.get_set(result.id, user.id).items == []
    summary = "".join([chunk async for chunk in service.stream_summary(result, user)])
    assert "本轮候选中暂未找到符合需求" in summary
    provider.stream_chat.assert_not_called()
