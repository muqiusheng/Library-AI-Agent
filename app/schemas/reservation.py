from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.db.models.enums import ReservationStatus


class ReservationCreate(BaseModel):
    holding_id: UUID


class ReservationRead(BaseModel):
    id: UUID
    holding_id: UUID
    book_id: UUID
    book_title: str
    collection_location: str | None
    call_number: str | None
    status: ReservationStatus
    expires_at: datetime
    is_mock: bool
    created_at: datetime


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    title: str
    content: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class UnreadCount(BaseModel):
    count: int
