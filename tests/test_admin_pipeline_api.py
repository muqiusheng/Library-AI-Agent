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
def pipeline_client() -> Iterator[TestClient]:
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
            student_no = f"pipeline-admin-{uuid4().hex[:8]}"
            session.add(
                User(
                    student_no=student_no,
                    password_hash=hash_password("correct horse battery staple"),
                    role=UserRole.ADMIN,
                    is_active=True,
                )
            )
            session.commit()
            login = client.post(
                "/api/v1/auth/login",
                json={
                    "student_no": student_no,
                    "password": "correct horse battery staple",
                },
            )
            client.headers["Authorization"] = f"Bearer {login.json()['data']['access_token']}"
            yield client
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()


def test_admin_upload_rejects_extension_and_fake_xlsx(pipeline_client: TestClient) -> None:
    wrong_extension = pipeline_client.post(
        "/api/v1/admin/imports",
        headers={"X-File-Name": "library.csv", "Content-Type": "application/octet-stream"},
        content=b"PK fake",
    )
    assert wrong_extension.status_code == 415
    assert wrong_extension.json()["error"]["code"] == "INVALID_FILE_TYPE"

    fake_xlsx = pipeline_client.post(
        "/api/v1/admin/imports",
        headers={"X-File-Name": "library.xlsx", "Content-Type": "application/octet-stream"},
        content=b"not a zip workbook",
    )
    assert fake_xlsx.status_code == 415
    assert fake_xlsx.json()["error"]["code"] == "INVALID_XLSX"


def test_admin_overview_and_setting_whitelist_hide_secrets(
    pipeline_client: TestClient,
) -> None:
    overview = pipeline_client.get("/api/v1/admin/system/overview")
    assert overview.status_code == 200
    assert overview.json()["data"]["published_books"] > 0

    settings = pipeline_client.get("/api/v1/admin/system/settings")
    assert settings.status_code == 200
    lowered = settings.text.lower()
    assert "api_key" not in lowered
    assert "deepseek" not in lowered

    updated = pipeline_client.patch(
        "/api/v1/admin/system/settings",
        json={"settings": {"recommendation_top_k": 3, "reservation_expiry_days": 5}},
    )
    assert updated.status_code == 200
    values = {item["key"]: item["value"] for item in updated.json()["data"]}
    assert values["recommendation_top_k"] == 3
    assert values["reservation_expiry_days"] == 5

    rejected = pipeline_client.patch(
        "/api/v1/admin/system/settings",
        json={"settings": {"deepseek_api_key": "must-not-be-accepted"}},
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "SETTING_NOT_ALLOWED"
    assert "must-not-be-accepted" not in rejected.text
