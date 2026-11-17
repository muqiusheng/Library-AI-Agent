from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from test_conversation_memory import answer, recommendation, send
from test_conversation_memory import memory_session as memory_session

from app.db.models import Book, Holding
from app.schemas.conversation import LearningNeedState
from app.services.conversation_constraint_service import ConversationConstraintService
from app.services.conversation_context_service import ConversationContextService
from app.services.need_clarification_service import NeedClarificationService, NeedExtraction

REAL_EXTRACT = NeedClarificationService._extract


def extraction_sequence(monkeypatch, *extractions):
    extract = AsyncMock(side_effect=extractions)
    monkeypatch.setattr(NeedClarificationService, "_extract", extract)
    return extract


def need(fixture):
    session, _, conversation = fixture
    return ConversationConstraintService(session).get(conversation).learning_need


@pytest.mark.asyncio
async def test_goal_first_then_complete_reply_recommends(memory_session, monkeypatch):
    extraction_sequence(monkeypatch,
        NeedExtraction(topic="Python", scenario="learning"),
        NeedExtraction(learning_goal="客户流失预测项目", foundation="会 Python，机器学习刚入门",
                       scenario="research"),
    )
    first = await send(memory_session, "我想学 Python")
    assert "做什么" in answer(first)
    assert not any(kind == "recommendation_ready" for kind, _ in first)
    second = await send(memory_session, "做客户流失预测项目，会 Python，机器学习刚入门")
    assert "客户流失预测项目" in recommendation(second)["query"]
    assert need(memory_session).pending_fields == []
    assert need(memory_session).clarification_rounds == 1
    assert sum(kind == "message_end" for kind, _ in second) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("text,status", [("不知道", "unknown"), ("跳过", "skipped")])
async def test_control_answers_work_without_model_and_do_not_invent_values(
    memory_session, monkeypatch, text, status,
):
    extract = extraction_sequence(monkeypatch, NeedExtraction(topic="Python"))
    await send(memory_session, "我想学 Python")
    second = await send(memory_session, text)
    assert "相关基础" in answer(second)
    assert need(memory_session).field_status["learning_goal"] == status
    assert need(memory_session).learning_goal is None
    assert extract.call_count == 1
    third = await send(memory_session, text)
    assert recommendation(third)
    assert need(memory_session).foundation is None
    assert need(memory_session).field_status["foundation"] == status
    assert need(memory_session).clarification_rounds == 2


@pytest.mark.asyncio
async def test_any_only_applies_to_current_preference(memory_session, monkeypatch):
    session, _, conversation = memory_session
    ConversationConstraintService(session).save_learning_need(conversation, LearningNeedState(
        topic="Python", pending_fields=["content_preference"],
        asked_fields=["learning_goal", "foundation", "content_preference"],
        clarification_rounds=2,
    ))
    extract = extraction_sequence(monkeypatch)
    events = await send(memory_session, "都可以")
    assert recommendation(events)
    state = need(memory_session)
    assert state.content_preference == "any"
    assert state.foundation is None
    assert state.field_status["foundation"] == "unset"
    extract.assert_not_called()


@pytest.mark.asyncio
async def test_missing_topic_is_not_raw_message_or_cancellation(memory_session, monkeypatch):
    extract = extraction_sequence(monkeypatch, NeedExtraction())
    events = await send(memory_session, "推荐几本书")
    assert "哪个主题" in answer(events)
    assert need(memory_session).topic is None
    assert need(memory_session).pending_fields == ["topic"]
    assert need(memory_session).clarification_rounds == 0
    events = await send(memory_session, "直接推荐")
    assert "哪个主题" in answer(events)
    assert not any(kind == "recommendation_ready" for kind, _ in events)
    assert extract.call_count == 1


@pytest.mark.asyncio
async def test_explicit_direct_and_cancel_bypass_extraction(memory_session, monkeypatch):
    extract = extraction_sequence(monkeypatch, NeedExtraction(topic="Python"))
    await send(memory_session, "我想学 Python")
    assert recommendation(await send(memory_session, "直接推荐"))
    cancelled = await send(memory_session, "取消")
    assert "已取消" in answer(cancelled)
    assert need(memory_session).topic is None
    assert need(memory_session).pending_fields == []
    assert extract.call_count == 1


@pytest.mark.asyncio
async def test_failed_extraction_preserves_pending_state(memory_session, monkeypatch):
    session, user, conversation = memory_session
    extraction_sequence(monkeypatch, NeedExtraction(topic="Python"), None)
    service = NeedClarificationService(session)
    await service.process(conversation, user, "我想学 Python")
    before = need(memory_session).model_dump()
    result = await service.process(conversation, user, "用于论文")
    assert result.action == "error"
    assert "尚未执行" in result.question
    assert need(memory_session).model_dump() == before


@pytest.mark.asyncio
async def test_real_extractor_uses_one_structured_call_and_pending_context(
    memory_session, monkeypatch,
):
    from types import SimpleNamespace

    session, user, conversation = memory_session
    monkeypatch.setattr(NeedClarificationService, "_extract", REAL_EXTRACT)
    structured = AsyncMock(return_value=NeedExtraction(topic="Python"))
    service = NeedClarificationService(
        session, SimpleNamespace(available=True, structured=structured),
    )
    result = await service.process(conversation, user, "我想学 Python")
    assert result.action == "ask"
    structured.assert_awaited_once()
    messages, schema = structured.call_args.args
    assert schema is NeedExtraction
    assert "field_status" in messages[0]["content"]
    assert "latest_message" in messages[1]["content"]


@pytest.mark.asyncio
async def test_topic_change_while_waiting_resets_topic_state(memory_session, monkeypatch):
    session, user, conversation = memory_session
    extraction_sequence(monkeypatch,
        NeedExtraction(topic="Python", foundation="零基础"),
        NeedExtraction(topic="Java", new_topic=True, scenario="exam"),
    )
    await send(memory_session, "推荐 Python 图书，只看可借")
    await send(memory_session, "换成 Java 考试参考书")
    state = need(memory_session)
    assert state.topic == "Java"
    assert state.foundation is None
    assert state.clarification_rounds == 1
    assert state.scenario == "exam"
    context = ConversationContextService(session).build(conversation, user)
    assert not context.constraints.only_available


@pytest.mark.asyncio
async def test_goal_update_after_recommendation_updates_saved_need_without_new_questions(
    memory_session, monkeypatch,
):
    extraction_sequence(monkeypatch,
        NeedExtraction(topic="Python", learning_goal="课程练习", foundation="会 Python"),
        NeedExtraction(learning_goal="毕业论文，客户流失预测", scenario="research"),
    )
    assert recommendation(await send(memory_session, "推荐 Python 图书，用于课程练习，我会 Python"))
    second = await send(memory_session, "改为用于毕业论文的客户流失预测")
    assert "客户流失预测" in recommendation(second)["query"]
    assert need(memory_session).learning_goal == "毕业论文，客户流失预测"
    assert need(memory_session).pending_fields == []


def test_partial_reply_preserves_unanswered_fields_and_goal_changes():
    state = LearningNeedState(
        topic="机器学习", learning_goal="毕业论文，客户流失预测", pending_fields=["foundation",
                                                                                  "content_preference"],
        asked_fields=["foundation", "content_preference"],
    )
    state = NeedClarificationService._merge(state, NeedExtraction(content_preference="practice"))
    assert state.foundation is None
    assert state.field_status["foundation"] == "unset"
    assert state.learning_goal == "毕业论文，客户流失预测"
    state = NeedClarificationService._merge(state, NeedExtraction(
        learning_goal="毕业论文，客户流失预测，两周完成",
    ))
    assert "两周完成" in NeedClarificationService._build_query(state)
    state = NeedClarificationService._merge(state, NeedExtraction(cleared_fields=["learning_goal"]))
    assert state.learning_goal is None
    assert "客户流失" not in NeedClarificationService._build_query(state)


@pytest.mark.asyncio
@pytest.mark.parametrize("reply,accepted", [("可以", True), ("不要", False)])
async def test_empty_result_requires_consent_and_only_changes_proposed_filter(
    memory_session, reply, accepted,
):
    session, user, conversation = memory_session
    for holding in session.scalars(select(Holding).join(Book).where(Book.title.like("Python%"))):
        holding.book_status = "checked_out"
    session.commit()
    conditions = ConversationConstraintService(session)
    from app.schemas.conversation import ConstraintUpdate

    conditions.update(
        conversation, ConstraintUpdate(difficulty="beginner", excluded_terms=["Java"]),
    )
    first = await send(memory_session, "推荐 Python 图书，只看可借")
    assert recommendation(first)["items"] == []
    assert "是否取消" in answer(first)
    context = ConversationContextService(session).build(conversation, user)
    assert context.constraints.only_available is True
    assert context.task.pending_relaxation.only_available is False
    # Even a stale page toggle cannot override an explicit agreement in the conversation.
    second = await send(memory_session, reply, only_available=True)
    context = ConversationContextService(session).build(conversation, user)
    assert context.task.pending_relaxation is None
    assert context.constraints.only_available is (not accepted)
    assert context.constraints.difficulty == "beginner"
    assert context.constraints.excluded_terms == ["Java"]
    if accepted:
        assert recommendation(second)["items"]
    else:
        assert not any(kind == "recommendation_ready" for kind, _ in second)
        assert "保留现有条件" in answer(second)


@pytest.mark.asyncio
async def test_empty_retrieval_does_not_blame_availability_or_offer_implicit_changes(
    memory_session, monkeypatch,
):
    session, user, conversation = memory_session
    monkeypatch.setattr(
        "app.integrations.library.local.LocalLibraryAdapter.search_candidates", lambda *a, **k: [],
    )
    events = await send(memory_session, "推荐 Python 图书，只看可借")
    assert recommendation(events)["items"] == []
    assert "暂未找到" in answer(events)
    assert "都因" not in answer(events)
    context = ConversationContextService(session).build(conversation, user)
    assert context.task.pending_relaxation is None
    assert ConversationConstraintService(session).get(conversation).only_available


@pytest.mark.asyncio
async def test_retrying_old_empty_result_does_not_attach_proposal_to_new_topic(memory_session):
    from test_recommendation_phase_two import retry, trace

    session, user, conversation = memory_session
    for holding in session.scalars(select(Holding).join(Book).where(Book.title.like("Python%"))):
        holding.book_status = "checked_out"
    session.commit()
    old = await send(memory_session, "推荐 Python 图书，只看可借")
    assert recommendation(old)["items"] == []
    await send(memory_session, "另外推荐 Java 图书")
    from app.core.errors import AppError

    with pytest.raises(AppError, match="最新一轮"):
        await retry(memory_session, trace(old)["turn_id"], "generating")
    context = ConversationContextService(session).build(conversation, user)
    assert context.task.topic.casefold() == "java"
    assert context.task.pending_relaxation is None
