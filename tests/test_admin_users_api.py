from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import SystemSetting, User, UserRole
from app.db.session import engine, get_db
from app.main import app

PASSWORD = "SafePass123!"


@pytest.fixture
def user_admin_client() -> Iterator[tuple[TestClient, Session, User]]:
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
            super_admin = User(
                student_no=f"super-{uuid4().hex[:8]}",
                password_hash=hash_password(PASSWORD),
                role=UserRole.SUPER_ADMIN,
                is_active=True,
            )
            session.add(super_admin)
            session.commit()
            login = client.post(
                "/api/v1/auth/login",
                json={"student_no": super_admin.student_no, "password": PASSWORD},
            )
            client.headers["Authorization"] = f"Bearer {login.json()['data']['access_token']}"
            yield client, session, super_admin
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


def test_super_admin_can_manage_users(
    user_admin_client: tuple[TestClient, Session, User],
) -> None:
    client, _session, _super_admin = user_admin_client
    student_no = f"managed-{uuid4().hex[:8]}"
    created = client.post(
        "/api/v1/admin/users/admins",
        json={"student_no": student_no, "display_name": "普通管理员", "password": PASSWORD},
    )
    assert created.status_code == 201
    assert created.json()["data"]["role"] == "admin"
    assert "password" not in created.text.lower()
    user_id = created.json()["data"]["id"]

    listed = client.get("/api/v1/admin/users", params={"query": student_no})
    assert listed.status_code == 200
    assert [item["student_no"] for item in listed.json()["data"]] == [student_no]

    disabled = client.patch(f"/api/v1/admin/users/{user_id}", json={"is_active": False})
    assert disabled.status_code == 200
    assert disabled.json()["data"]["is_active"] is False

    reset = client.post(
        f"/api/v1/admin/users/{user_id}/reset-password",
        json={"password": "NewPass456!"},
    )
    assert reset.status_code == 200
    assert "NewPass456!" not in reset.text

    initial_invite = client.get("/api/v1/admin/users/registration-invite")
    assert initial_invite.status_code == 200
    assert initial_invite.json()["data"]["configured"] is False

    generated = client.post("/api/v1/admin/users/registration-invite/generate")
    assert generated.status_code == 200
    invite_code = generated.json()["data"]["code"]
    assert len(invite_code) == 12
    stored_invite = _session.get(SystemSetting, "registration_invite")
    assert stored_invite is not None
    assert invite_code not in str(stored_invite.value_json)

    registration = {
        "student_no": f"invited-{uuid4().hex[:8]}",
        "password": "SafePass123!",
        "profile": {
            "grade": "大一",
            "major": "计算机科学与技术",
            "foundation": "入门",
            "learning_goals": ["课程学习"],
        },
    }
    rejected = client.post("/api/v1/auth/register", json=registration)
    assert rejected.status_code == 403
    assert rejected.json()["error"]["code"] == "INVALID_REGISTRATION_CODE"
    accepted = client.post(
        "/api/v1/auth/register", json={**registration, "registration_code": invite_code}
    )
    assert accepted.status_code == 201


def test_normal_admin_cannot_manage_users(
    user_admin_client: tuple[TestClient, Session, User],
) -> None:
    client, session, _super_admin = user_admin_client
    normal = User(
        student_no=f"normal-{uuid4().hex[:8]}",
        password_hash=hash_password(PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(normal)
    session.commit()
    login = client.post(
        "/api/v1/auth/login", json={"student_no": normal.student_no, "password": PASSWORD}
    )
    client.headers["Authorization"] = f"Bearer {login.json()['data']['access_token']}"

    forbidden = client.get("/api/v1/admin/users")
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "SUPER_ADMIN_REQUIRED"
    invite_forbidden = client.post("/api/v1/admin/users/registration-invite/generate")
    assert invite_forbidden.status_code == 403
