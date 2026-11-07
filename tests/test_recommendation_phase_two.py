import json
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from test_conversation_memory import memory_session as memory_session
from test_conversation_memory import recommendation, send

from app.api.v1.conversations import retry_recommendation, stream_message
from app.core.errors import AppError
from app.db.models import Book, Message, MessageRole, RecommendationSet, User
from app.schemas.conversation import MessageCreate, RecommendationRetry
from app.services.effective_profile_service import EffectiveProfileService
from app.services.profile_memory_service import ProfileMemoryService
from app.services.recommendation_progress import exclude_profile_facts
from app.services.recommendation_service import RecommendationService


async def consume(response):
    events = []
    async for block in response.body_iterator:
        if isinstance(block, bytes):
            block = block.decode()
        lines = block.strip().splitlines()
        events.append((lines[0].removeprefix("event: "), json.loads(lines[1][6:])))
    return events


def trace(events):
    return [value for kind, value in events if kind == "analysis"][-1]


async def retry(fixture, turn_id, stage, excluded=None):
    session, user, conversation = fixture
    response = await retry_recommendation(
        conversation.id,
        UUID(turn_id),
        RecommendationRetry(stage=stage, excluded_profile_keys=excluded),
        SimpleNamespace(state=SimpleNamespace(request_id="phase-two")),
        user,
        session,
    )
    events = await consume(response)
    assert not [data for kind, data in events if kind == "error"], events
    return events


@pytest.mark.asyncio
async def test_stage_retries_reuse_work_and_update_the_same_reply(memory_session, monkeypatch):
    session, _, conversation = memory_session
    first = await send(memory_session, "推荐 Python 项目图书")
    turn_id = trace(first)["turn_id"]
    original_reply = next(data["message_id"] for kind, data in first if kind == "message_end")

    def no_search(*args, **kwargs):
        raise AssertionError("阶段重试不应重新检索")

    monkeypatch.setattr(
        "app.integrations.library.local.LocalLibraryAdapter.search_candidates", no_search
    )
    compared = await retry(memory_session, turn_id, "comparing")
    assert trace(compared)["retry_from"] == "comparing"
    assert next(s for s in trace(compared)["steps"] if s["id"] == "retrieving")["reused"]

    async def no_rank(*args, **kwargs):
        raise AssertionError("文案重试不应重新排序")

    monkeypatch.setattr(RecommendationService, "_rerank", no_rank)
    generated = await retry(memory_session, turn_id, "generating")
    assert recommendation(generated)["id"] == recommendation(compared)["id"]
    assert trace(generated)["attempt"] == 3
    assert (
        next(data["message_id"] for kind, data in generated if kind == "message_end")
        == original_reply
    )
    messages = list(
        session.scalars(select(Message).where(Message.conversation_id == conversation.id))
    )
    assert len(messages) == 2
    assert sum(message.role == MessageRole.USER for message in messages) == 1


@pytest.mark.asyncio
async def test_one_turn_exclusion_masks_all_model_inputs_and_can_be_restored(memory_session):
    session, user, _ = memory_session
    user.profile.foundation = "学过 Python；了解 Java 基础"
    session.commit()
    first = await send(memory_session, "推荐 Python 项目图书")
    turn_id = trace(first)["turn_id"]
    masked = await retry(memory_session, turn_id, "retrieving", ["topic:python"])
    value = trace(masked)
    assert not any(f["key"] == "topic:python" for f in value["profile_evidence"])
    assert value["excluded_profile_evidence"][0]["key"] == "topic:python"
    stored = session.get(RecommendationSet, UUID(recommendation(masked)["id"]))
    assert "python" not in stored.profile_snapshot["abilities"]
    assert "java" in stored.profile_snapshot["abilities"]
    assert "Python" not in stored.profile_snapshot["foundation"]
    assert "foundation_background" not in stored.profile_snapshot
    assert "topic:python" not in stored.profile_snapshot["sources"]
    assert all("evidence" not in source for source in stored.profile_snapshot["sources"].values())
    assert "python" in EffectiveProfileService(session).build(user)["abilities"]
    restored = await retry(memory_session, turn_id, "retrieving", [])
    assert any(f["key"] == "topic:python" for f in trace(restored)["profile_evidence"])
    # The exclusion must never become a permanent conversation preference.
    next_turn = await send(memory_session, "再推荐 Python 图书")
    assert trace(next_turn)["excluded_profile_keys"] == []


@pytest.mark.asyncio
async def test_registration_fact_correction_preserves_other_abilities_and_invalidates_reuse(
    memory_session,
):
    session, user, _ = memory_session
    user.profile.foundation = "学过 Python；了解 Java 基础"
    session.commit()
    first = await send(memory_session, "推荐 Python 项目图书")
    python = next(f for f in trace(first)["profile_evidence"] if f["key"] == "topic:python")
    service = ProfileMemoryService(session)
    service.correct_fact(
        user, "topic:python", {**python["value_json"], "level": "none"}, python["value_json"]
    )
    profile = EffectiveProfileService(session).build(user)
    assert profile["abilities"]["python"]["level"] == "none"
    assert profile["abilities"]["java"]["level"] == "basic"
    assert profile["sources"]["topic:python"]["source"] == "manual"
    rerun = await retry(memory_session, trace(first)["turn_id"], "generating")
    assert trace(rerun)["retry_from"] == "retrieving"
    assert "画像" in trace(rerun)["retry_note"]
    assert recommendation(rerun)["id"] != recommendation(first)["id"]
    with pytest.raises(AppError) as error:
        service.correct_fact(
            user,
            "topic:python",
            {**python["value_json"], "level": "advanced"},
            python["value_json"],
        )
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_filter_ledger_and_candidate_comparison_match_actual_results(memory_session):
    events = await send(memory_session, "推荐 Python 图书", only_available=True)
    final = trace(events)
    stats = final["filter_stats"]
    remaining = stats["retrieved"]
    for step in stats["steps"]:
        assert step["before"] == remaining
        remaining -= step["removed"]
        assert step["remaining"] == remaining
    assert remaining == stats["retained"]
    chosen = [candidate for candidate in final["candidates"] if candidate["selected"]]
    assert len(chosen) == stats["selected"] == len(recommendation(events)["items"])
    assert [book["book_id"] for book in chosen] == [
        book["book_id"] for book in recommendation(events)["items"]
    ]
    assert any(not book["selected"] for book in final["candidates"])
    assert all(book["available_count"] > 0 for book in chosen)


def test_filter_counts_do_not_double_count_overlapping_reasons():
    books = [
        SimpleNamespace(
            id=i,
            title="不需要" if i == 3 else "Python",
            description="",
            holdings=[]
            if i == 4
            else [SimpleNamespace(book_status="available", circulation_status="lendable")],
        )
        for i in range(1, 6)
    ]
    service = RecommendationService(
        SimpleNamespace(), library=SimpleNamespace(), llm=SimpleNamespace()
    )
    kept, steps = service._filter_candidates(books, {1}, {1, 2}, ["不需要"], True)
    assert [book.id for book in kept] == [5]
    assert [step["removed"] for step in steps] == [1, 1, 1, 1]


def test_fact_correction_reports_list_limits_without_changing_the_profile(memory_session):
    session, user, _ = memory_session
    before = list(EffectiveProfileService(session).build(user)["learning_goals"])
    with pytest.raises(AppError) as error:
        ProfileMemoryService(session).correct_fact(
            user, "learning_goals", [f"目标{i}" for i in range(21)], before
        )
    assert error.value.status_code == 422
    assert EffectiveProfileService(session).build(user)["learning_goals"] == before


@pytest.mark.asyncio
async def test_failed_comparison_is_saved_and_resumes_without_search(memory_session, monkeypatch):
    session, user, conversation = memory_session
    original_rank = RecommendationService._rerank

    async def broken(*args, **kwargs):
        raise RuntimeError("比较暂不可用")

    monkeypatch.setattr(RecommendationService, "_rerank", broken)
    response = await stream_message(
        conversation.id,
        MessageCreate(content="推荐 Python 图书"),
        SimpleNamespace(state=SimpleNamespace(request_id="failure")),
        user,
        session,
    )
    failed = await consume(response)
    final = trace(failed)
    assert final["status"] == "error"
    assert "comparing" in final["retry_stages"]
    stored = session.scalar(select(Message).where(Message.role == MessageRole.ASSISTANT))
    assert stored.structured_payload["analysis"]["status"] == "error"
    monkeypatch.setattr(RecommendationService, "_rerank", original_rank)

    def no_search(*args, **kwargs):
        raise AssertionError("应复用失败前的检索结果")

    monkeypatch.setattr(
        "app.integrations.library.local.LocalLibraryAdapter.search_candidates", no_search
    )
    retried = await retry(memory_session, final["turn_id"], "comparing")
    assert trace(retried)["status"] == "complete"


@pytest.mark.asyncio
async def test_changed_availability_restarts_filtering_before_summary_retry(memory_session):
    session, _, _ = memory_session
    first = await send(memory_session, "推荐 Python 图书", only_available=True)
    book = session.get(Book, UUID(recommendation(first)["items"][0]["book_id"]))
    for holding in book.holdings:
        holding.book_status = "unavailable"
    session.commit()
    second = await retry(memory_session, trace(first)["turn_id"], "generating")
    assert trace(second)["retry_from"] == "retrieving"
    assert all(item["available_count"] > 0 for item in recommendation(second)["items"])


@pytest.mark.asyncio
async def test_failed_recomparison_invalidates_the_old_summary_checkpoint(
    memory_session, monkeypatch
):
    session, user, conversation = memory_session
    first = await send(memory_session, "推荐 Python 图书")

    async def broken(*args, **kwargs):
        raise RuntimeError("新的比较尚未完成")

    monkeypatch.setattr(RecommendationService, "_rerank", broken)
    response = await retry_recommendation(
        conversation.id,
        UUID(trace(first)["turn_id"]),
        RecommendationRetry(stage="comparing"),
        SimpleNamespace(state=SimpleNamespace(request_id="recomparison")),
        user,
        session,
    )
    events = await consume(response)
    assert trace(events)["status"] == "error"
    assert trace(events)["retry_stages"] == ["retrieving", "comparing"]
    stored = session.scalar(select(Message).where(Message.role == MessageRole.ASSISTANT))
    assert "recommendation_set_id" not in stored.structured_payload


@pytest.mark.asyncio
async def test_retry_rejects_other_users_and_superseded_turns(memory_session):
    session, user, conversation = memory_session
    first = await send(memory_session, "推荐 Python 图书")
    stranger = User(student_no=uuid4().hex, password_hash="unused")
    session.add(stranger)
    session.commit()
    with pytest.raises(AppError) as error:
        await retry_recommendation(
            conversation.id,
            UUID(trace(first)["turn_id"]),
            RecommendationRetry(),
            SimpleNamespace(state=SimpleNamespace(request_id="other")),
            stranger,
            session,
        )
    assert error.value.status_code == 404
    await send(memory_session, "推荐 Java 图书")
    with pytest.raises(AppError) as error:
        await retry(memory_session, trace(first)["turn_id"], "retrieving")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_changed_filter_on_retry_restarts_search_and_persists_the_condition(memory_session):
    from app.services.conversation_constraint_service import ConversationConstraintService

    session, user, conversation = memory_session
    first = await send(memory_session, "推荐 Python 图书", only_available=True)
    response = await retry_recommendation(
        conversation.id,
        UUID(trace(first)["turn_id"]),
        RecommendationRetry(stage="generating", only_available=False),
        SimpleNamespace(state=SimpleNamespace(request_id="changed-filter")),
        user,
        session,
    )
    events = await consume(response)
    assert not [data for kind, data in events if kind == "error"]
    assert trace(events)["retry_from"] == "retrieving"
    availability = next(
        step for step in trace(events)["filter_stats"]["steps"] if step["id"] == "availability"
    )
    assert availability["applied"] is False
    assert ConversationConstraintService(session).get(conversation).only_available is False


def test_exclusion_removes_background_and_source_backdoors_without_mutation():
    profile = {
        "abilities": {"python": {"topic": "Python", "level": "basic"}},
        "foundation": "学过 Python",
        "foundation_background": "学过 Python",
        "sources": {"major": {"evidence": "我学过 Python，专业是计算机"}},
    }
    masked = exclude_profile_facts(profile, ["topic:python"])
    assert masked["foundation"] == ""
    assert "evidence" not in masked["sources"]["major"]
    assert "python" in profile["abilities"]
