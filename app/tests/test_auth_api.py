from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.models import User, UserRole
from app.db.session import engine, get_db
from app.main import app


@pytest.fixture
def auth_client() -> Iterator[TestClient]:
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
            yield client
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


def registration_payload(student_no: str) -> dict:
    return {
        "student_no": student_no,
        "password": "SafePass123!",
        "display_name": "测试学生",
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
    }


def test_register_duplicate_login_and_current_user(auth_client: TestClient) -> None:
    student_no = f"s{uuid4().hex[:10]}"
    payload = registration_payload(student_no)

    registered = auth_client.post(
        "/api/v1/auth/register",
        json=payload,
        headers={"X-Request-ID": "register-request"},
    )
    assert registered.status_code == 201
    assert registered.json()["request_id"] == "register-request"
    assert registered.json()["data"]["student_no"] == student_no
    assert registered.json()["data"]["profile"]["major"] == "计算机科学与技术"
    assert "password" not in registered.text.lower()

    duplicate = auth_client.post("/api/v1/auth/register", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "STUDENT_NO_EXISTS"

    wrong_password = auth_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": "wrong-password"},
    )
    assert wrong_password.status_code == 401
    assert wrong_password.json()["error"]["code"] == "INVALID_CREDENTIALS"

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": payload["password"]},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    assert login.json()["data"]["token_type"] == "bearer"
    assert "deepseek" not in login.text.lower()
    assert "api_key" not in login.text.lower()

    current_user = auth_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert current_user.status_code == 200
    assert current_user.json()["data"]["student_no"] == student_no


def test_authentication_and_rbac_status_codes(auth_client: TestClient) -> None:
    anonymous = auth_client.get("/api/v1/auth/me")
    assert anonymous.status_code == 401
    assert anonymous.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"

    student_no = f"s{uuid4().hex[:10]}"
    payload = registration_payload(student_no)
    auth_client.post("/api/v1/auth/register", json=payload)
    login = auth_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": payload["password"]},
    )
    student_token = login.json()["data"]["access_token"]
    forbidden = auth_client.get(
        "/api/v1/admin/access-check",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "ADMIN_REQUIRED"


def test_admin_can_access_admin_dependency(auth_client: TestClient) -> None:
    student_no = f"admin-{uuid4().hex[:8]}"
    session = next(app.dependency_overrides[get_db]())
    session.add(
        User(
            student_no=student_no,
            password_hash=hash_password("correct horse battery staple"),
            role=UserRole.ADMIN,
            is_active=True,
        )
    )
    session.commit()

    login = auth_client.post(
        "/api/v1/auth/login",
        json={"student_no": student_no, "password": "correct horse battery staple"},
    )
    token = login.json()["data"]["access_token"]
    allowed = auth_client.get(
        "/api/v1/admin/access-check",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert allowed.status_code == 200
    assert allowed.json()["data"]["role"] == "admin"


def test_validation_error_does_not_echo_password(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/v1/auth/register",
        json={**registration_payload("short-pass-user"), "password": "secret"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "secret" not in response.text
