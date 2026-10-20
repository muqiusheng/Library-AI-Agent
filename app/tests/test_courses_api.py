from fastapi.testclient import TestClient

from app.main import app


def test_public_course_catalog_exposes_stable_adapter_contract() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/catalog/courses", params={"query": "Java"})

    assert response.status_code == 200
    items = response.json()["data"]
    assert items == [
        {
            "code": "CS302",
            "name": "Java Web 应用开发",
            "category": "专业方向",
            "source": "local",
        }
    ]
