from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, MemorySource, Message, MessageRole, MessageType, User
from app.db.session import engine, get_db
from app.main import app
from app.services.profile_memory_service import ProfileMemoryService


@pytest.fixture
def profile_client() -> Iterator[tuple[TestClient, Session]]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        autoflush=False,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    def override_get_db() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


def _create_user(client: TestClient) -> tuple[str, dict[str, str]]:
    student_no = f"memory-{uuid4().hex[:10]}"
    password = "SafePass123!"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "student_no": student_no,
            "password": password,
            "profile": {
                "grade": "大一",
                "major": "计算机科学与技术",
                "foundation": "了解基础概念",
                "learning_goals": ["完成课程项目"],
                "interests": [],
                "difficulty_preference": "progressive",
                "courses": [],
                "read_books": [],
            },
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    token = login.json()["data"]["access_token"]
    return student_no, {"Authorization": f"Bearer {token}"}


def _message(session: Session, user: User, content: str) -> Message:
    conversation = Conversation(user_id=user.id, title="画像测试")
    session.add(conversation)
    session.flush()
    message = Message(
        conversation_id=conversation.id,
        role=MessageRole.USER,
        message_type=MessageType.TEXT,
        content=content,
    )
    session.add(message)
    session.commit()
    return message


def test_conversation_memory_manual_priority_history_and_temporary_filter(
    profile_client: tuple[TestClient, Session],
) -> None:
    client, session = profile_client
    student_no, headers = _create_user(client)
    user = session.scalar(select(User).where(User.student_no == student_no))
    assert user is not None
    service = ProfileMemoryService(session)

    created = service.extract_from_message(user, _message(session, user, "我没学过 Java"))
    assert len(created) == 1
    assert created[0].value_json["level"] == "none"

    active = client.get("/api/v1/profile", headers=headers)
    assert active.status_code == 200
    memory = active.json()["data"]["memories"][0]
    assert memory["source"] == "conversation"

    edited = client.patch(
        f"/api/v1/profile/memories/{memory['id']}",
        headers=headers,
        json={"value_json": {"topic": "Java", "level": "beginner", "label": "已有入门基础"}},
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["source"] == MemorySource.MANUAL.value
    assert edited.json()["data"]["is_user_edited"] is True

    assert not service.extract_from_message(user, _message(session, user, "Java 零基础"))
    assert not service.extract_from_message(
        user, _message(session, user, "这次我没学过 Python，只看可借图书")
    )

    history = client.get("/api/v1/profile?include_history=true", headers=headers).json()["data"]
    java_memories = [item for item in history["memories"] if item["key"] == "topic:java"]
    assert len(java_memories) == 2
    assert sum(item["is_active"] for item in java_memories) == 1
    assert (
        next(item for item in java_memories if item["is_active"])["value_json"]["level"]
        == "beginner"
    )

    _, other_headers = _create_user(client)
    forbidden = client.patch(
        f"/api/v1/profile/memories/{edited.json()['data']['id']}",
        headers=other_headers,
        json={"value_json": "越权修改"},
    )
    assert forbidden.status_code == 404
