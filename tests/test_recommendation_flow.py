import json
from collections.abc import Iterator
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.services.recommendation_service as recommendation_module
from app.core.security import hash_password
from app.db.models import Book, DataVersion, DataVersionStatus, Holding, User, UserRole
from app.db.session import engine, get_db
from app.main import app


class UnconfiguredDeepSeek:
    available = False
    settings = SimpleNamespace(deepseek_chat_model="deepseek-v4-flash")


@pytest.fixture
def flow_client(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[TestClient, Session]]:
    monkeypatch.setattr(recommendation_module, "DeepSeekProvider", UnconfiguredDeepSeek)
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


def _register_and_login(client: TestClient) -> dict[str, str]:
    student_no = f"flow-{uuid4().hex[:10]}"
    password = "SafePass123!"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "student_no": student_no,
            "password": password,
            "display_name": "主链路测试用户",
            "profile": {
                "grade": "大一",
                "major": "计算机科学与技术",
                "foundation": "Java 零基础",
                "learning_goals": ["学习 Java 入门"],
                "interests": ["项目案例"],
                "difficulty_preference": "beginner",
                "courses": [],
                "read_books": [],
            },
        },
    )
    assert registered.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def _recommendation_event(response_text: str) -> dict:
    blocks = response_text.replace("\r\n", "\n").split("\n\n")
    for block in blocks:
        lines = block.splitlines()
        if "event: recommendation_ready" in lines:
            data = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
            return json.loads(data)
    raise AssertionError(f"recommendation_ready event missing: {response_text}")


def test_real_top_five_available_fallback_and_user_isolation(
    flow_client: tuple[TestClient, Session],
) -> None:
    client, session = flow_client
    user_a = _register_and_login(client)
    user_b = _register_and_login(client)
    created = client.post("/api/v1/conversations", json={}, headers=user_a)
    assert created.status_code == 201
    conversation_id = created.json()["data"]["id"]

    streamed = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "我想从零学习 Java，只看在馆可借的书", "only_available": True},
        headers=user_a,
    )
    assert streamed.status_code == 200
    recommendation = _recommendation_event(streamed.text)
    items = recommendation["items"]
    assert len(items) == 5
    assert all(item["available_count"] > 0 for item in items)

    book_ids = {item["book_id"] for item in items}
    stored_ids = {
        str(value) for value in session.scalars(select(Book.id).where(Book.id.in_(book_ids)))
    }
    assert stored_ids == book_ids

    set_id = recommendation["id"]
    assert client.get(f"/api/v1/recommendations/{set_id}", headers=user_a).status_code == 200
    assert client.get(f"/api/v1/recommendations/{set_id}", headers=user_b).status_code == 404
    assert (
        client.get(f"/api/v1/conversations/{conversation_id}/messages", headers=user_b).status_code
        == 404
    )


def test_feedback_state_and_conversation_constraints_affect_next_round(
    flow_client: tuple[TestClient, Session],
) -> None:
    client, _session = flow_client
    headers = _register_and_login(client)
    conversation_id = client.post(
        "/api/v1/conversations", json={}, headers=headers
    ).json()["data"]["id"]
    first_stream = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "推荐 Java 入门图书", "only_available": False},
        headers=headers,
    )
    first = _recommendation_event(first_stream.text)
    excluded_book = first["items"][0]["book_id"]
    completed_book = first["items"][1]["book_id"]

    not_interested = client.post(
        f"/api/v1/recommendations/{first['id']}/feedback",
        json={"book_id": excluded_book, "type": "not_interested"},
        headers=headers,
    )
    assert not_interested.status_code == 200
    too_hard = client.post(
        f"/api/v1/recommendations/{first['id']}/feedback",
        json={"book_id": completed_book, "type": "too_hard"},
        headers=headers,
    )
    assert too_hard.status_code == 200
    completed = client.put(
        f"/api/v1/user-books/{completed_book}/state",
        json={"state": "completed"},
        headers=headers,
    )
    assert completed.status_code == 200

    second_stream = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "简单一点，只看可借的 Java 图书", "only_available": True},
        headers=headers,
    )
    second = _recommendation_event(second_stream.text)
    second_ids = {item["book_id"] for item in second["items"]}
    assert excluded_book not in second_ids
    assert completed_book not in second_ids
    assert all(item["available_count"] > 0 for item in second["items"])

    constraints = client.get(
        f"/api/v1/conversations/{conversation_id}/constraints", headers=headers
    )
    assert constraints.json()["data"] == {
        "only_available": True,
        "difficulty": "beginner",
        "excluded_terms": [],
    }


def test_learning_path_only_uses_candidates_and_progress_is_consistent(
    flow_client: tuple[TestClient, Session],
) -> None:
    client, _session = flow_client
    owner = _register_and_login(client)
    other = _register_and_login(client)
    conversation_id = client.post(
        "/api/v1/conversations", json={}, headers=owner
    ).json()["data"]["id"]
    stream = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "Java 零基础学习路线", "only_available": True},
        headers=owner,
    )
    recommendation = _recommendation_event(stream.text)
    candidate_ids = {item["book_id"] for item in recommendation["items"]}

    created = client.post(
        "/api/v1/learning-paths",
        json={"recommendation_set_id": recommendation["id"]},
        headers=owner,
    )
    assert created.status_code == 201
    path = created.json()["data"]
    assert [stage["position"] for stage in path["stages"]] == [1, 2, 3]
    path_book_ids = {
        book["book_id"] for stage in path["stages"] for book in stage["books"]
    }
    assert path_book_ids == candidate_ids
    assert client.get(f"/api/v1/learning-paths/{path['id']}", headers=other).status_code == 404

    ordered_books = [book for stage in path["stages"] for book in stage["books"]]
    for index, book in enumerate(ordered_books, start=1):
        updated = client.patch(
            f"/api/v1/learning-paths/{path['id']}/books/{book['book_id']}",
            json={"state": "completed"},
            headers=owner,
        )
        assert updated.status_code == 200
        assert updated.json()["data"]["progress"] == index * 20
    assert updated.json()["data"]["status"] == "completed"


def test_mock_reservation_cancel_notifications_and_user_isolation(
    flow_client: tuple[TestClient, Session],
) -> None:
    client, session = flow_client
    owner = _register_and_login(client)
    other = _register_and_login(client)
    holding_id = session.scalar(
        select(Holding.id)
        .join(Book, Book.id == Holding.book_id)
        .join(DataVersion, DataVersion.id == Book.data_version_id)
        .where(
            DataVersion.status == DataVersionStatus.PUBLISHED,
            Holding.book_status == "available",
            Holding.circulation_status == "lendable",
        )
        .limit(1)
    )
    assert holding_id is not None

    created = client.post(
        "/api/v1/reservations", json={"holding_id": str(holding_id)}, headers=owner
    )
    assert created.status_code == 200
    reservation = created.json()["data"]
    assert reservation["is_mock"] is True
    assert client.get("/api/v1/notifications/unread-count", headers=owner).json()["data"] == {
        "count": 1
    }

    forbidden = client.delete(f"/api/v1/reservations/{reservation['id']}", headers=other)
    assert forbidden.status_code == 404
    cancelled = client.delete(f"/api/v1/reservations/{reservation['id']}", headers=owner)
    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["status"] == "cancelled"

    notifications = client.get("/api/v1/notifications", headers=owner).json()["data"]
    assert len(notifications) == 2
    assert all("模拟" in item["title"] or "模拟" in item["content"] for item in notifications)
    client.post("/api/v1/notifications/read-all", headers=owner)
    assert client.get("/api/v1/notifications/unread-count", headers=owner).json()["data"] == {
        "count": 0
    }


def test_anonymous_evaluation_scores_and_admin_summary(
    flow_client: tuple[TestClient, Session],
) -> None:
    client, session = flow_client
    owner = _register_and_login(client)
    conversation_id = client.post(
        "/api/v1/conversations", json={}, headers=owner
    ).json()["data"]["id"]
    stream = client.post(
        f"/api/v1/conversations/{conversation_id}/messages/stream",
        json={"content": "数据库课程拓展阅读", "only_available": True},
        headers=owner,
    )
    recommendation = _recommendation_event(stream.text)
    payload = {
        "tester_code": f"tester-{uuid4().hex[:8]}",
        "profile_scenario": "大二计算机学生学习数据库",
        "recommendation_set_id": recommendation["id"],
        "relevance_score": 5,
        "difficulty_score": 4,
        "reason_score": 4,
        "holding_score": 5,
        "satisfaction_score": 4,
        "notes": "匿名验收样本",
    }
    created = client.post("/api/v1/evaluations", json=payload)
    assert created.status_code == 201
    assert "user_id" not in created.text
    assert client.post("/api/v1/evaluations", json=payload).status_code == 409
    assert client.post(
        "/api/v1/evaluations", json={**payload, "tester_code": "bad-score", "reason_score": 6}
    ).status_code == 422

    admin_no = f"evaluation-admin-{uuid4().hex[:8]}"
    session.add(
        User(
            student_no=admin_no,
            password_hash=hash_password("correct horse battery staple"),
            role=UserRole.ADMIN,
            is_active=True,
        )
    )
    session.commit()
    login = client.post(
        "/api/v1/auth/login",
        json={"student_no": admin_no, "password": "correct horse battery staple"},
    )
    admin = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    summary = client.get("/api/v1/admin/evaluations/summary", headers=admin)
    assert summary.status_code == 200
    assert summary.json()["data"]["sample_size"] >= 1
    assert 1 <= summary.json()["data"]["averages"]["satisfaction"] <= 5
    assert summary.json()["data"]["satisfaction_distribution"]["4"] >= 1
