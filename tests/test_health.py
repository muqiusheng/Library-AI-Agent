from fastapi.testclient import TestClient

from app.main import app


def test_health_has_dependency_status_and_request_id() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "test-request"
    payload = response.json()
    assert payload["success"] is True
    assert payload["request_id"] == "test-request"
    assert payload["data"]["status"] in {"ok", "degraded"}
    assert payload["data"]["database"]["status"] in {"ok", "unavailable"}
    assert payload["data"]["vector_store"]["status"] == "ok"
