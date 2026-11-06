import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import MetaData, create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles, deregister
from sqlalchemy.orm import Session

from app.api.v1.conversations import stream_message
from app.core.errors import AppError
from app.db.base import Base
from app.db.models import (
    Book,
    Conversation,
    DataVersion,
    DataVersionStatus,
    Holding,
    Message,
    RecommendationSet,
    User,
    UserProfile,
)
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import ConstraintUpdate, MessageCreate, TurnResolution
from app.services.conversation_constraint_service import ConversationConstraintService
from app.services.conversation_context_service import ConversationContextService
from app.services.conversation_turn_service import ConversationTurnService


class OfflineProvider:
    available = False
    settings = SimpleNamespace(deepseek_chat_model="test-offline")


@pytest.fixture
def memory_session(monkeypatch):
    # SQLite is used only for isolated tests; production remains PostgreSQL JSONB.
    @compiles(JSONB, "sqlite")
    def compile_jsonb(element, compiler, **kwargs):
        return "JSON"

    engine = create_engine("sqlite://")
    metadata = MetaData()
    for table in Base.metadata.sorted_tables:
        table.to_metadata(metadata)
    seen = set()
    for table in metadata.tables.values():
        for index in table.indexes:
            if index.name in seen:
                index.name += "_isolated"
            seen.add(index.name)
    metadata.create_all(engine)
    for module in (
        "conversation_turn_service",
        "general_chat_service",
        "profile_memory_service",
        "recommendation_service",
    ):
        monkeypatch.setattr(f"app.services.{module}.DeepSeekProvider", OfflineProvider)
    monkeypatch.setattr(
        "app.integrations.library.local.ChromaVectorStore",
        lambda *args: SimpleNamespace(query=lambda **kwargs: []),
    )
    with Session(engine, expire_on_commit=False) as session:
        user = User(student_no="memory-user", password_hash="unused")
        user.profile = UserProfile(
            grade="大一",
            major="计算机",
            foundation="基础较弱",
            learning_goals=["课程项目"],
            interests=[],
        )
        session.add(user)
        version = DataVersion(name="isolated", status=DataVersionStatus.PUBLISHED)
        session.add(version)
        session.flush()
        for topic in ("Java", "Python"):
            for i in range(12):
                book = Book(
                    data_version_id=version.id,
                    title=f"{topic} 实践 {i}",
                    normalized_title=f"{topic.lower()} {i}",
                    source_fingerprint=uuid4().hex,
                    description=f"{topic} 入门练习和项目",
                )
                book.holdings = [
                    Holding(
                        source_row_no=1,
                        book_status="available",
                        circulation_status="lendable",
                        current_location="测试馆藏室",
                    )
                ]
                session.add(book)
        conversation = Conversation(user_id=user.id, title="记忆测试")
        session.add(conversation)
        session.commit()
        yield session, user, conversation
    engine.dispose()
    deregister(JSONB)


async def send(fixture, content, **kwargs):
    session, user, conversation = fixture
    response = await stream_message(
        conversation.id,
        MessageCreate(content=content, **kwargs),
        SimpleNamespace(state=SimpleNamespace(request_id="test")),
        user,
        session,
    )
    events = []
    async for block in response.body_iterator:
        if isinstance(block, bytes):
            block = block.decode()
        lines = block.strip().splitlines()
        events.append(
            (lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: ")))
        )
    assert not [data for event, data in events if event == "error"], events
    return events


def recommendation(events):
    return next(data for event, data in events if event == "recommendation_ready")


def answer(events):
    return "".join(data["content"] for event, data in events if event == "text_delta")


@pytest.mark.asyncio
async def test_omitted_topic_conditions_cancel_and_reload(memory_session):
    session, user, conversation = memory_session
    await send(memory_session, "推荐 Java 图书")
    second = recommendation(await send(memory_session, "再简单一点，只看可借"))
    assert "java" in second["query"].lower()
    assert all("Java" in book["title"] for book in second["items"])
    session.expire_all()
    restored = ConversationContextService(session).build(conversation, user)
    assert restored.constraints.difficulty == "beginner"
    assert restored.constraints.only_available is True
    assert restored.task.topic.lower() == "java"
    await send(memory_session, "取消限制")
    restored = ConversationContextService(session).build(conversation, user)
    assert restored.constraints.difficulty is None
    assert restored.constraints.only_available is False
    assert restored.task.topic.lower() == "java"


@pytest.mark.asyncio
async def test_replace_only_selected_book_and_reject_previous_batch(memory_session):
    first = recommendation(await send(memory_session, "推荐 Java 图书"))
    second = recommendation(await send(memory_session, "不要第一本，换一本"))
    old_ids = [book["book_id"] for book in first["items"]]
    new_ids = [book["book_id"] for book in second["items"]]
    assert len(new_ids) == len(old_ids) == 5
    assert new_ids[0] != old_ids[0]
    assert new_ids[1:] == old_ids[1:]
    third = recommendation(await send(memory_session, "换一批"))
    assert not set(new_ids) & {book["book_id"] for book in third["items"]}
    assert old_ids[0] not in {book["book_id"] for book in third["items"]}


@pytest.mark.asyncio
async def test_reference_queries_current_holdings_without_new_recommendation(memory_session):
    session, _, _ = memory_session
    first = recommendation(await send(memory_session, "推荐 Java 图书"))
    from uuid import UUID

    book = session.get(Book, UUID(first["items"][1]["book_id"]))
    book.holdings[0].book_status = "checked_out"
    session.commit()
    events = await send(memory_session, "第二本现在能借吗")
    assert book.title in answer(events)
    assert "0 个可借副本" in answer(events)
    assert not any(event == "recommendation_ready" for event, _ in events)
    explained = await send(memory_session, "为什么推荐第二本")
    assert book.title in answer(explained)
    assert len(list(session.scalars(select(RecommendationSet)))) == 1
    followup = await send(memory_session, "它能借吗")
    assert book.title in answer(followup)
    assert "0 个可借副本" in answer(followup)


@pytest.mark.asyncio
async def test_ambiguous_or_out_of_range_reference_requires_clarification(memory_session):
    await send(memory_session, "推荐 Java 图书")
    for text in ("这本能借吗", "第九本能借吗", "换一本"):
        events = await send(memory_session, text)
        assert "第几本" in answer(events)
        assert not any(event == "recommendation_ready" for event, _ in events)


@pytest.mark.asyncio
async def test_new_topic_resets_constraints_unless_explicitly_retained(memory_session):
    session, user, conversation = memory_session
    await send(memory_session, "推荐 Java 图书，只看可借")
    await send(memory_session, "简单一点")
    events = await send(memory_session, "换成 Python 图书，其他要求不变")
    assert all("Python" in book["title"] for book in recommendation(events)["items"])
    context = ConversationContextService(session).build(conversation, user)
    assert context.constraints.only_available
    assert context.constraints.difficulty == "beginner"
    await send(memory_session, "另外推荐 Java 图书")
    context = ConversationContextService(session).build(conversation, user)
    assert not context.constraints.only_available
    assert context.constraints.difficulty is None


@pytest.mark.asyncio
async def test_explicit_false_cancels_but_omission_preserves_available_filter(memory_session):
    session, user, conversation = memory_session
    await send(memory_session, "推荐 Java 图书", only_available=True)
    await send(memory_session, "简单一点")
    assert ConversationConstraintService(session).get(conversation).only_available
    await send(memory_session, "再推荐 Java 图书", only_available=False)
    assert not ConversationConstraintService(session).get(conversation).only_available
    assert user.id == conversation.user_id


def test_constraint_patch_preserves_task_and_can_clear_difficulty(memory_session):
    session, _, conversation = memory_session
    constraints = ConversationConstraintService(session)
    constraints.update(conversation, ConstraintUpdate(difficulty="beginner"))
    conversation.constraints.constraints_json = {
        **conversation.constraints.constraints_json,
        "_task": {"topic": "Java"},
    }
    session.commit()
    constraints.update(conversation, ConstraintUpdate(difficulty=None))
    assert conversation.constraints.constraints_json["_task"] == {"topic": "Java"}
    assert constraints.get(conversation).difficulty is None
    constraints.update_from_message(conversation, "Java 和 Python 都可以", only_available=None)
    assert constraints.get(conversation).only_available is False


def test_history_limit_and_user_isolation(memory_session):
    session, user, conversation = memory_session
    repository = ConversationRepository(session)
    from app.services.conversation_service import ConversationService

    for i in range(20):
        ConversationService(session).add_user_message(conversation, str(i))
    assert [m.content for m in repository.recent_messages(conversation.id, user.id, 3)] == [
        "17",
        "18",
        "19",
    ]
    with pytest.raises(AppError):
        repository.recent_messages(conversation.id, uuid4())
    assert len(list(session.scalars(select(Message)))) == 20


@pytest.mark.asyncio
async def test_structured_resolution_uses_history_and_validates_reference(memory_session):
    session, user, conversation = memory_session
    await send(memory_session, "推荐 Java 图书")
    context = ConversationContextService(session).build(conversation, user)
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=TurnResolution(
                action="availability",
                target_rank=99,
            )
        ),
    )
    result = await ConversationTurnService(provider).resolve(context, "那本能借吗")
    assert result.action == "clarify"
    messages = provider.structured.call_args.args[0]
    assert "Java" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "那本能借吗"}
    provider.structured.side_effect = RuntimeError("provider unavailable")
    result = await ConversationTurnService(provider).resolve(context, "简单一点")
    assert result.action == "refine"
    assert result.topic.lower() == "java"


@pytest.mark.asyncio
async def test_negative_available_phrase_and_explain_whole_list(memory_session):
    session, _, conversation = memory_session
    first = recommendation(await send(memory_session, "推荐 Java 图书，只看可借"))
    await send(memory_session, "不必只看可借")
    assert not ConversationConstraintService(session).get(conversation).only_available
    events = await send(memory_session, "为什么推荐这些书")
    assert "Java" in answer(events)
    assert not any(event == "recommendation_ready" for event, _ in events)
    assert first["items"]


@pytest.mark.asyncio
async def test_model_resolution_reaches_search_with_inherited_topic(memory_session, monkeypatch):
    session, user, conversation = memory_session
    await send(memory_session, "推荐 Java 图书")
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=TurnResolution(
                action="refine",
                topic="Java",
                standalone_query="Java 课程项目练习",
                constraints=ConstraintUpdate(difficulty="beginner"),
            )
        ),
    )
    monkeypatch.setattr(
        "app.services.conversation_turn_service.DeepSeekProvider",
        lambda: provider,
    )
    result = recommendation(await send(memory_session, "要适合新手，最好有项目练习"))
    assert "Java 课程项目练习" in result["query"]
    assert "beginner" in result["query"]
    assert all("Java" in book["title"] for book in result["items"])
    context = ConversationContextService(session).build(conversation, user)
    assert context.task.request == "Java 课程项目练习"


@pytest.mark.asyncio
async def test_clarification_reply_resumes_pending_task(memory_session, monkeypatch):
    events = await send(memory_session, "Agent")
    assert not any(event == "recommendation_ready" for event, _ in events)
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=TurnResolution(
                action="recommend",
                topic="人工智能 Agent",
                standalone_query="人工智能 Agent 开发图书",
            )
        ),
    )
    monkeypatch.setattr(
        "app.services.conversation_turn_service.DeepSeekProvider",
        lambda: provider,
    )
    await send(memory_session, "人工智能方向，想找书")
    prompt = provider.structured.call_args.args[0][0]["content"]
    assert '"pending_question": "Agent"' in prompt
    session, user, conversation = memory_session
    assert not ConversationContextService(session).build(conversation, user).task.pending_question


@pytest.mark.asyncio
async def test_profile_extraction_uses_prior_owned_messages_and_preserves_manual_fact(
    memory_session,
):
    from app.services.conversation_service import ConversationService
    from app.services.profile_fact_extractor import ProfileExtraction, ProfileFact
    from app.services.profile_memory_service import ProfileMemoryService

    session, user, conversation = memory_session
    messages = ConversationService(session)
    messages.add_assistant_message(conversation, "你学过 Python 吗？")
    current = messages.add_user_message(conversation, "没有")
    messages.add_assistant_message(conversation, "未来的消息：你学过 Java 吗？")
    candidate = ProfileFact(
        category="foundation",
        topic="Python编程",
        value_json='{"level":"none"}',
        subject="user",
        scope="persistent",
        evidence="没有",
        confidence=0.95,
    )
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=ProfileExtraction(facts=[candidate]),
        ),
    )
    service = ProfileMemoryService(session, provider)
    created = await service.extract_from_message(user, current)
    assert len(created) == 1
    assert created[0].key == "topic:python"
    assert created[0].source_message_id == current.id
    assert created[0].value_json["level"] == "none"
    prompt_messages = provider.structured.call_args.args[0]
    assert prompt_messages[-2] == {"role": "assistant", "content": "你学过 Python 吗？"}
    assert not any("未来" in item["content"] for item in prompt_messages)
    assert user.profile.foundation == "基础较弱"

    manual = service.edit_memory(
        user.id,
        created[0].id,
        {
            "topic": "Python",
            "level": "basic",
            "label": "已学习基础",
        },
    )
    later = messages.add_user_message(conversation, "我没学过 Python")
    provider.structured.return_value = ProfileExtraction(
        facts=[
            candidate.model_copy(
                update={
                    "evidence": "我没学过 Python",
                }
            )
        ]
    )
    assert await service.extract_from_message(user, later) == []
    assert manual.is_active
    assert manual.value_json["level"] == "basic"

    other = User(student_no="different-profile-user", password_hash="unused")
    session.add(other)
    session.commit()
    with pytest.raises(AppError):
        await service.extract_from_message(other, later)


@pytest.mark.asyncio
async def test_stream_entry_extracts_short_answer_with_history(memory_session, monkeypatch):
    from app.db.models import ProfileMemory
    from app.services.conversation_service import ConversationService
    from app.services.profile_fact_extractor import ProfileExtraction, ProfileFact

    session, _, conversation = memory_session
    ConversationService(session).add_assistant_message(conversation, "你学过 Python 吗？")
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
                        evidence="没有",
                        confidence=0.95,
                    )
                ],
            )
        ),
    )
    monkeypatch.setattr("app.services.profile_memory_service.DeepSeekProvider", lambda: provider)
    await send(memory_session, "没有")
    memories = list(session.scalars(select(ProfileMemory)))
    assert len(memories) == 1
    assert memories[0].value_json["level"] == "none"
    assert provider.structured.call_count == 1
