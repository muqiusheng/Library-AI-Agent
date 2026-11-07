import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest
from test_conversation_memory import memory_session as memory_session
from test_conversation_memory import recommendation, send

from app.db.models import Message
from app.services.profile_fact_extractor import ExtractedMemory
from app.services.recommendation_progress import RecommendationProgress, profile_evidence
from app.services.recommendation_service import RecommendationService


@pytest.fixture
def python_extraction(monkeypatch):
    # The isolated pipeline fixture disables model calls; supply its extraction result.
    monkeypatch.setattr(
        "app.services.profile_memory_service.DeepSeekProvider",
        lambda: SimpleNamespace(available=True),
    )

    async def extract(self, text, *, history):
        if "学过 Python" not in text:
            return []
        return [
            ExtractedMemory(
                category="foundation",
                key="topic:python",
                value={"topic": "Python", "level": "basic", "basis": "self_report"},
                confidence=0.95,
            )
        ]

    monkeypatch.setattr(
        "app.services.profile_memory_service.ProfileMemoryService._extract_async", extract
    )


@pytest.mark.asyncio
async def test_progress_matches_saved_recommendation_and_profile_sources(
    memory_session, python_extraction
):
    session, _, _ = memory_session
    events = await send(memory_session, "我学过 Python，推荐 Python 项目实践图书")
    traces = [data for kind, data in events if kind == "analysis"]
    result = recommendation(events)
    final = traces[-1]
    assert final["status"] == "complete"
    assert [step["id"] for step in final["steps"]] == [
        "understanding",
        "profile",
        "intent",
        "retrieving",
        "filtering",
        "comparing",
        "generating",
    ]
    assert all(step["status"] == "complete" for step in final["steps"])
    assert all(step["elapsed_ms"] >= 0 for step in final["steps"])
    python = next(fact for fact in final["profile_evidence"] if fact["key"] == "topic:python")
    assert python["source_label"] == "本次输入"
    assert "学过" in python["evidence"]
    assert "熟练程度未确认" in python["value"]
    for compared, book in zip(final["comparisons"], result["items"][:3], strict=True):
        assert compared["book_id"] == book["book_id"]
        assert compared["reason"] == book["reason"]
        assert compared["method"] == "rule"
        assert compared["available_count"] == book["available_count"]
    end = next(data for kind, data in events if kind == "message_end")
    stored = session.get(Message, UUID(end["message_id"]))
    assert stored.structured_payload["analysis"] == final
    assert stored.structured_payload["recommendation_set_id"] == result["id"]
    # Intermediate snapshots must not mutate when the final snapshot is completed.
    assert traces[0]["status"] == "running"
    assert traces[0]["steps"][0]["status"] == "running"


@pytest.mark.asyncio
async def test_history_sources_and_empty_candidates_are_truthful(
    memory_session, python_extraction, monkeypatch
):
    await send(memory_session, "我学过 Python")
    monkeypatch.setattr(
        "app.integrations.library.local.LocalLibraryAdapter.search_candidates",
        lambda *args, **kwargs: [],
    )
    events = await send(memory_session, "推荐 Python 项目实践图书")
    final = [data for kind, data in events if kind == "analysis"][-1]
    python = next(fact for fact in final["profile_evidence"] if fact["key"] == "topic:python")
    assert python["source_label"] == "历史对话"
    assert final["comparisons"] == []
    assert "暂未找到" in final["summary"]
    assert final["status"] == "complete"


def test_irrelevant_abilities_and_unsourced_defaults_are_not_displayed():
    facts = profile_evidence(
        {
            "abilities": {"java": {"topic": "Java", "level": "advanced"}},
            "difficulty_preference": "progressive",
        },
        "Python 项目",
    )
    assert facts == []


def test_timer_stops_and_error_stage_is_not_marked_complete(monkeypatch):
    clock = [10.0]
    monkeypatch.setattr("app.services.recommendation_progress.perf_counter", lambda: clock[0])
    progress = RecommendationProgress()
    progress.update({"stage": "retrieving", "label": "正在检索馆藏"})
    clock[0] = 12.0
    progress.update({"stage": "comparing", "label": "正在比较适配程度"})
    clock[0] = 15.0
    final = progress.finish("error")
    clock[0] = 99.0
    assert progress.snapshot() == final
    assert final["elapsed_ms"] == 5000
    assert [step["elapsed_ms"] for step in final["steps"]] == [2000, 3000]
    assert [step["status"] for step in final["steps"]] == ["complete", "error"]


@pytest.mark.asyncio
async def test_milestones_stream_before_work_finishes_and_close_cancels_worker():
    service = RecommendationService(
        SimpleNamespace(), library=SimpleNamespace(), llm=SimpleNamespace()
    )
    cancelled = asyncio.Event()

    async def recommend(*, on_progress):
        try:
            await on_progress({"stage": "comparing"})
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    service.recommend = recommend
    events = service.recommend_events()
    kind, data = await asyncio.wait_for(anext(events), timeout=1)
    assert kind == "progress" and data["stage"] == "comparing"
    await events.aclose()
    assert cancelled.is_set()


@pytest.mark.asyncio
async def test_recommendation_worker_errors_propagate_to_stream():
    service = RecommendationService(
        SimpleNamespace(), library=SimpleNamespace(), llm=SimpleNamespace()
    )

    async def recommend(*, on_progress):
        await on_progress({"stage": "retrieving"})
        raise RuntimeError("检索失败")

    service.recommend = recommend
    events = service.recommend_events()
    assert (await anext(events))[0] == "progress"
    with pytest.raises(RuntimeError, match="检索失败"):
        await anext(events)
