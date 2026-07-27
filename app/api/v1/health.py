from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import engine

router = APIRouter(tags=["system"])


class DependencyHealth(BaseModel):
    status: Literal["ok", "unavailable"]
    detail: str | None = None


class HealthData(BaseModel):
    status: Literal["ok", "degraded"]
    database: DependencyHealth
    vector_store: DependencyHealth


class HealthResponse(BaseModel):
    success: bool = True
    data: HealthData
    request_id: str


def _database_health() -> DependencyHealth:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return DependencyHealth(status="ok")
    except Exception as exc:
        return DependencyHealth(status="unavailable", detail=exc.__class__.__name__)


def _vector_health() -> DependencyHealth:
    try:
        path = get_settings().chroma_persist_directory
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".healthcheck"
        probe.touch(exist_ok=True)
        return DependencyHealth(status="ok")
    except OSError as exc:
        return DependencyHealth(status="unavailable", detail=exc.__class__.__name__)


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    database = _database_health()
    vector_store = _vector_health()
    status = "ok" if database.status == vector_store.status == "ok" else "degraded"
    return HealthResponse(
        data=HealthData(status=status, database=database, vector_store=vector_store),
        request_id=request.state.request_id,
    )
