from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from sqlalchemy import select
from test_conversation_memory import answer, recommendation, send
from test_conversation_memory import memory_session as memory_session

from app.db.models import (
    Book,
    BookTag,
    Conversation,
    MemorySource,
    ProfileMemory,
    RecommendationSet,
    User,
)
from app.schemas.profile import ProfileUpdate
from app.services.conversation_context_service import ConversationContextService
from app.services.effective_profile_service import EffectiveProfileService
from app.services.profile_fact_extractor import ProfileExtraction, ProfileFact
from app.services.profile_memory_service import ProfileMemoryService
from app.services.recommendation_service import RecommendationService


def store(fixture, topic, level, manual=False):
    session, user, _ = fixture
    result = ProfileMemoryService(session)._replace_active(
        user_id=user.id,
        category="foundation",
        key=topic,
        value={"topic": topic, "level": level},
        source=MemorySource.MANUAL if manual else MemorySource.CONVERSATION,
        confidence=1.0,
        source_message_id=None,
        user_edited=manual,
        protect_manual=not manual,
    )
    session.commit()
    return result


def test_normalized_corrections_versions_noop_and_deleted_aliases(memory_session):
    session, user, _ = memory_session
    old = store(memory_session, "Python 编程", "none")
    assert store(memory_session, "python", "none") is None
    new = store(memory_session, "Python语言", "basic")
    assert not old.is_active and new.is_active
    session.expire_all()
    profile = EffectiveProfileService(session).build(user)
    assert list(profile["abilities"]) == ["python"]
    assert profile["abilities"]["python"]["level"] == "basic"
    assert profile["sources"]["topic:python"]["memory_id"] == str(new.id)
    ProfileMemoryService(session).deactivate_memory(user.id, new.id)
    assert "python" not in EffectiveProfileService(session).build(user)["abilities"]


def test_legacy_aliases_manual_priority_and_no_revival(memory_session):
    session, user, _ = memory_session
    now = datetime.now(UTC)
    rows = [
        ProfileMemory(
            user_id=user.id,
            category="foundation",
            key=key,
            value_json={"topic": topic, "level": level},
            source=MemorySource.MANUAL if manual else MemorySource.CONVERSATION,
            confidence=1.0,
            is_active=True,
            is_user_edited=manual,
            created_at=now + timedelta(seconds=i),
        )
        for i, (key, topic, level, manual) in enumerate(
            [
                ("topic:Python编程", "Python 编程", "beginner", True),
                ("topic:PYTHON", "python", "none", False),
            ]
        )
    ]
    session.add_all(rows)
    session.commit()
    assert EffectiveProfileService(session).build(user)["abilities"]["python"]["level"] == "basic"
    ProfileMemoryService(session).deactivate_memory(user.id, rows[1].id)
    assert "python" not in EffectiveProfileService(session).build(user)["abilities"]


def test_manual_field_updates_and_add_remove_goals(memory_session):
    session, user, _ = memory_session
    service = ProfileMemoryService(session)
    service.update_profile(user, ProfileUpdate(major="软件工程", foundation="Python 零基础"))
    profile = EffectiveProfileService(session).build(user)
    assert profile["major"] == "软件工程"
    assert profile["abilities"]["python"]["level"] == "none"
    assert (
        service._replace_active(
            user_id=user.id,
            category="major",
            key="major",
            value="数学",
            source=MemorySource.CONVERSATION,
            confidence=0.9,
            source_message_id=None,
            user_edited=False,
            protect_manual=True,
        )
        is None
    )
    assert service.conflicts
    assert EffectiveProfileService(session).build(user)["major"] == "软件工程"
    for value, operation in [
        (["Python 编程"], "add"),
        (["课程项目"], "add"),
        (["Python"], "remove"),
    ]:
        service._replace_active(
            user_id=user.id,
            category="learning_goals",
            key="learning_goals",
            value=value,
            source=MemorySource.CONVERSATION,
            confidence=0.9,
            source_message_id=None,
            user_edited=False,
            protect_manual=True,
            operation=operation,
        )
        session.commit()
    assert "Python" not in EffectiveProfileService(session).build(user)["learning_goals"]


def test_manual_conflict_is_rechecked_before_confirmation(memory_session):
    session, user, _ = memory_session
    manual = store(memory_session, "Python", "basic", manual=True)
    service = ProfileMemoryService(session)
    assert (
        service._replace_active(
            user_id=user.id,
            category="foundation",
            key="topic:python",
            value={"topic": "Python", "level": "none"},
            source=MemorySource.CONVERSATION,
            confidence=0.95,
            source_message_id=None,
            user_edited=False,
            protect_manual=True,
        )
        is None
    )
    proposals = service.conflicts
    assert proposals[0]["protected_memory_id"] == str(manual.id)
    service.edit_memory(user.id, manual.id, {"topic": "Python", "level": "advanced"})
    assert not service.confirm_conflicts(user, proposals)
    assert (
        EffectiveProfileService(session).build(user)["abilities"]["python"]["level"] == "advanced"
    )


def test_other_users_and_new_conversations_have_correct_profile(memory_session):
    session, user, _ = memory_session
    store(memory_session, "Python", "none")
    conversation = Conversation(user_id=user.id, title="新的会话")
    other = User(student_no="other-effective-profile", password_hash="unused")
    session.add_all([conversation, other])
    session.commit()
    assert (
        ConversationContextService(session)
        .build(conversation, user)
        .profile["abilities"]["python"]["level"]
        == "none"
    )
    assert EffectiveProfileService(session).build(other)["abilities"] == {}


def tagged_books(fixture):
    session, _, _ = fixture
    books = list(session.scalars(select(Book).where(Book.title.like("Python%"))))
    for i, book in enumerate(books):
        book.tags = [
            BookTag(
                tag_type="difficulty",
                tag_value="beginner" if i < 6 else "advanced",
                confidence=1.0,
                source="test",
            )
        ]
    session.commit()


@pytest.mark.asyncio
async def test_actual_ranking_changes_with_ability_and_current_override(memory_session):
    session, user, conversation = memory_session
    tagged_books(memory_session)
    service = RecommendationService(session)
    store(memory_session, "Python", "none")
    beginner = await service.recommend(
        user=user, conversation_id=conversation.id, query="Python 图书"
    )
    assert all(item.difficulty == "beginner" for item in beginner.items)
    store(memory_session, "Python", "advanced")
    advanced = await service.recommend(
        user=user, conversation_id=conversation.id, query="Python 图书"
    )
    assert all(item.difficulty == "advanced" for item in advanced.items)
    assert {item.book_id for item in beginner.items}.isdisjoint(
        item.book_id for item in advanced.items
    )
    store(memory_session, "Python", "none")
    explicit = await service.recommend(
        user=user,
        conversation_id=conversation.id,
        query="Python 进阶书",
        constraints={"difficulty": "advanced"},
    )
    assert all(item.difficulty == "advanced" for item in explicit.items)
    assert "自述" in explicit.items[0].reason
    persisted = session.get(RecommendationSet, beginner.id)
    assert persisted.profile_snapshot["abilities"]["python"]["level"] == "none"


def test_ability_in_other_domain_does_not_change_difficulty(memory_session):
    session, user, _ = memory_session
    store(memory_session, "Python", "none")
    profile = EffectiveProfileService(session).build(user)
    assert (
        RecommendationService._effective_preference(user, [], None, profile=profile, query="Java")
        == "progressive"
    )
    assert (
        RecommendationService._effective_preference(
            user, [], None, profile=profile, query="LangChain"
        )
        == "beginner"
    )


@pytest.mark.asyncio
async def test_same_turn_fact_is_used_before_intent_and_recommendation(memory_session, monkeypatch):
    session, user, _ = memory_session
    tagged_books(memory_session)
    text = "我没学过 Python，推荐 Python 图书"
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=ProfileExtraction(
                facts=[
                    ProfileFact(
                        category="foundation",
                        topic="Python",
                        value_json='{"level":"none"}',
                        subject="user",
                        scope="persistent",
                        evidence="我没学过 Python",
                        confidence=0.95,
                    ),
                ]
            )
        ),
    )
    monkeypatch.setattr("app.services.profile_memory_service.DeepSeekProvider", lambda: provider)
    result = recommendation(await send(memory_session, text))
    assert all(item["difficulty"] == "beginner" for item in result["items"])
    row = session.get(RecommendationSet, UUID(result["id"]))
    assert row.profile_snapshot["abilities"]["python"]["level"] == "none"


@pytest.mark.asyncio
async def test_conflicting_manual_fact_requires_explicit_yes(memory_session, monkeypatch):
    session, user, _ = memory_session
    store(memory_session, "Python", "basic", manual=True)
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=ProfileExtraction(
                facts=[
                    ProfileFact(
                        category="foundation",
                        topic="Python",
                        value_json='{"level":"none"}',
                        subject="user",
                        scope="persistent",
                        evidence="我没学过 Python",
                        confidence=0.95,
                    ),
                ]
            )
        ),
    )
    monkeypatch.setattr("app.services.profile_memory_service.DeepSeekProvider", lambda: provider)
    events = await send(memory_session, "我没学过 Python")
    assert "是否更新画像" in answer(events)
    assert EffectiveProfileService(session).build(user)["abilities"]["python"]["level"] == "basic"
    await send(memory_session, "保留原画像")
    assert EffectiveProfileService(session).build(user)["abilities"]["python"]["level"] == "basic"
    await send(memory_session, "我没学过 Python")
    confirmed = await send(memory_session, "确认更新")
    assert "已更新" in answer(confirmed)
    assert EffectiveProfileService(session).build(user)["abilities"]["python"]["level"] == "none"


@pytest.mark.asyncio
async def test_online_rewrite_rerank_and_summary_share_effective_snapshot(memory_session):
    session, user, conversation = memory_session
    store(memory_session, "Python", "none")
    captured = []

    class Model:
        available = True
        settings = SimpleNamespace(deepseek_chat_model="simulated")

        async def structured(self, messages, schema):
            captured.append(messages)
            return (
                schema(keywords="Python")
                if schema.__name__ == "EnrichedQuery"
                else schema(items=[])
            )

        async def stream_chat(self, messages, **kwargs):
            captured.append(messages)
            yield "推荐说明"

    service = RecommendationService(session, llm=Model())
    result = await service.recommend(
        user=user, conversation_id=conversation.id, query="Python 图书"
    )
    assert len(captured) == 2
    assert all('"level": "none"' in messages[-1]["content"] for messages in captured)
    store(memory_session, "Python", "advanced")
    assert "".join([chunk async for chunk in service.stream_summary(result, user)]) == "推荐说明"
    assert '"level": "none"' in captured[-1][1]["content"]
    assert '"level": "advanced"' not in captured[-1][1]["content"]


@pytest.mark.asyncio
async def test_effective_profile_api_chat_and_history_edit_do_not_revive_old_versions(
    memory_session,
):
    from app.api.v1.profile import get_profile
    from app.services.general_chat_service import GeneralChatService

    session, user, conversation = memory_session
    old = store(memory_session, "Python", "none")
    current = store(memory_session, "Python", "basic")
    ProfileMemoryService(session).deactivate_memory(user.id, old.id)
    assert current.is_active
    response = get_profile(
        SimpleNamespace(state=SimpleNamespace(request_id="test")), user, session, False
    )
    data = response["data"]
    profile = (
        data.effective_profile if hasattr(data, "effective_profile") else data["effective_profile"]
    )
    assert profile["abilities"]["python"]["level"] == "basic"
    captured = []

    async def stream(messages, **kwargs):
        captured.append(messages)
        yield "回答"

    chat = GeneralChatService(session, SimpleNamespace(available=True, stream_chat=stream))
    assert [chunk async for chunk in chat.stream_answer(conversation, user, "我有哪些基础？")] == [
        "回答"
    ]
    assert '"level": "basic"' in captured[0][0]["content"]


@pytest.mark.asyncio
async def test_list_removal_and_addition_keep_current_utterance_order(memory_session):
    session, user, conversation = memory_session
    text = "我不再对 Python 感兴趣，我喜欢 Java"
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=ProfileExtraction(
                facts=[
                    ProfileFact(
                        category="interests",
                        topic="",
                        value_json='["Java"]',
                        subject="user",
                        scope="persistent",
                        evidence="我喜欢 Java",
                        confidence=0.95,
                    ),
                    ProfileFact(
                        category="interests",
                        topic="",
                        value_json='["Python"]',
                        subject="user",
                        scope="persistent",
                        evidence="我不再对 Python 感兴趣",
                        confidence=0.95,
                    ),
                ]
            )
        ),
    )
    from app.services.conversation_service import ConversationService

    message = ConversationService(session).add_user_message(conversation, text)
    await ProfileMemoryService(session, provider).extract_from_message(user, message)
    assert EffectiveProfileService(session).build(user)["interests"] == ["Java"]


def test_goal_update_changes_real_score_and_manual_foundation_replaces_old_facts(memory_session):
    session, user, _ = memory_session
    books = list(session.scalars(select(Book).where(Book.title.like("Python%"))))
    books[0].description = "Python 项目实践"
    books[1].description = "Python 理论原理"
    session.commit()
    service = RecommendationService(session)
    before = [service._score(book, "Python", user).scores.goal for book in books[:2]]
    assert before[0] > before[1]
    ProfileMemoryService(session).update_profile(user, ProfileUpdate(learning_goals=["理论原理"]))
    after = [service._score(book, "Python", user).scores.goal for book in books[:2]]
    assert after[0] < after[1]
    store(memory_session, "Python", "basic", manual=True)
    ProfileMemoryService(session).update_profile(user, ProfileUpdate(foundation="尚未明确现有基础"))
    assert not EffectiveProfileService(session).build(user)["abilities"]
    assert store(memory_session, "Python", "none") is not None


@pytest.mark.asyncio
async def test_explicit_difficulty_controls_retrieval_and_scoring(memory_session):
    session, user, conversation = memory_session
    store(memory_session, "Python", "none")
    service = RecommendationService(session)
    queries = []
    original = service.library.search_candidates

    def search(query, **kwargs):
        queries.append(query)
        return original(query, **kwargs)

    service.library.search_candidates = search
    await service.recommend(
        user=user,
        conversation_id=conversation.id,
        query="Python",
        constraints={"difficulty": "advanced"},
    )
    assert queries == ["Python"]


def test_legacy_low_confidence_fact_is_not_an_effective_ability(memory_session):
    session, user, _ = memory_session
    session.add(
        ProfileMemory(
            user_id=user.id,
            category="foundation",
            key="topic:Python",
            value_json={"topic": "Python", "level": "advanced"},
            source=MemorySource.CONVERSATION,
            confidence=0.2,
            is_active=True,
            is_user_edited=False,
        )
    )
    session.commit()
    assert "python" not in EffectiveProfileService(session).build(user)["abilities"]
