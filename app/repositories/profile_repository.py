from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import ProfileMemory


class ProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_memories(self, user_id: UUID, *, include_inactive: bool) -> list[ProfileMemory]:
        statement = select(ProfileMemory).where(ProfileMemory.user_id == user_id)
        if not include_inactive:
            statement = statement.where(ProfileMemory.is_active.is_(True))
        return list(self.session.scalars(statement.order_by(desc(ProfileMemory.created_at))))

    def get_owned_memory(self, memory_id: UUID, user_id: UUID) -> ProfileMemory | None:
        return self.session.scalar(
            select(ProfileMemory).where(
                ProfileMemory.id == memory_id,
                ProfileMemory.user_id == user_id,
            )
        )

    def active_for_key(self, user_id: UUID, category: str, key: str) -> ProfileMemory | None:
        return self.session.scalar(
            select(ProfileMemory)
            .where(
                ProfileMemory.user_id == user_id,
                ProfileMemory.category == category,
                ProfileMemory.key == key,
                ProfileMemory.is_active.is_(True),
            )
            .order_by(desc(ProfileMemory.created_at))
            .limit(1)
        )
