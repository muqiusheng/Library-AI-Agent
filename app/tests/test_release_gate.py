from pathlib import Path

from app.api.v1.conversations import _event
from app.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_openapi_contains_frontend_contract_paths() -> None:
    paths = set(app.openapi()["paths"])
    expected = {
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/conversations",
        "/api/v1/conversations/{conversation_id}/messages/stream",
        "/api/v1/recommendations/{set_id}",
        "/api/v1/books/{book_id}",
        "/api/v1/profile",
        "/api/v1/learning-paths",
        "/api/v1/reservations",
        "/api/v1/notifications/unread-count",
        "/api/v1/evaluations",
        "/api/v1/admin/imports",
        "/api/v1/admin/tags/reviews",
        "/api/v1/admin/system/overview",
        "/api/v1/admin/evaluations/summary",
    }
    assert expected <= paths


def test_sse_event_contract_is_stable() -> None:
    value = _event("recommendation_ready", {"id": "set-1", "items": []})
    assert value.startswith("event: recommendation_ready\n")
    assert 'data: {"id": "set-1", "items": []}\n\n' in value


def test_replaced_legacy_runtime_modules_are_absent() -> None:
    legacy = [
        "app/core/qianwen.py",
        "app/core/rag_engine.py",
        "app/core/session_manager.py",
        "app/api/v1/chat.py",
        "app/api/v1/books.py",
        "app/services/library_service.py",
        "app/services/recommend_service.py",
        "frontend/src/main.js",
        "frontend/src/router/index.js",
        "frontend/src/store/chat.js",
        "frontend/src/views/Chat.vue",
    ]
    assert not [name for name in legacy if (ROOT / name).exists()]

    runtime_files = [
        *[
            path
            for path in (ROOT / "app").rglob("*.py")
            if "tests" not in path.parts
        ],
        *list((ROOT / "frontend" / "src").rglob("*.ts")),
        *list((ROOT / "frontend" / "src").rglob("*.vue")),
    ]
    content = "\n".join(path.read_text(encoding="utf-8").casefold() for path in runtime_files)
    assert "vuex" not in content
    assert "qianwen" not in content


def test_home_production_entrypoint_is_loopback_only() -> None:
    compose = (ROOT / "docker-compose.home.yml").read_text(encoding="utf-8")
    assert '"127.0.0.1:8180:80"' in compose
    postgres_section, backend_section = compose.split("  backend:", 1)
    backend_section, _gateway_section = backend_section.split("  gateway:", 1)
    assert "ports:" not in postgres_section
    assert "ports:" not in backend_section


def test_production_frontend_uses_same_origin_api() -> None:
    client = (ROOT / "frontend" / "src" / "api" / "client.ts").read_text(encoding="utf-8")
    dockerfile = (ROOT / "frontend" / "Dockerfile.home").read_text(encoding="utf-8")
    assert "localhost:8000" not in client
    assert "vite preview" not in dockerfile
    assert "nginx" in dockerfile.casefold()
