from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.models import Conversation, Message


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_for_user(self, user_id: UUID) -> list[Conversation]:
        return list(
            self.session.scalars(
                select(Conversation)
                .where(Conversation.user_id == user_id, Conversation.archived_at.is_(None))
                .order_by(desc(Conversation.updated_at))
            )
        )

    def get_owned(self, conversation_id: UUID, user_id: UUID) -> Conversation:
        conversation = self.session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id, Conversation.user_id == user_id
            )
        )
        if conversation is None:
            raise AppError(status_code=404, code="CONVERSATION_NOT_FOUND", message="会话不存在")
        return conversation

    def messages(self, conversation_id: UUID, user_id: UUID) -> list[Message]:
        self.get_owned(conversation_id, user_id)
        return list(
            self.session.scalars(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
            )
        )

    def touch(self, conversation: Conversation) -> None:
        now = datetime.now(UTC)
        previous = conversation.updated_at
        if previous is not None:
            previous = previous.replace(tzinfo=UTC) if previous.tzinfo is None else previous
            now = max(now, previous)
        conversation.updated_at = now

    def recent_messages(
        self,
        conversation_id: UUID,
        user_id: UUID,
        limit: int = 12,
        *,
        before: datetime | None = None,
    ) -> list[Message]:
        self.get_owned(conversation_id, user_id)
        statement = select(Message).where(Message.conversation_id == conversation_id)
        if before is not None:
            statement = statement.where(Message.created_at < before)
        values = list(
            self.session.scalars(
                statement.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit)
            )
        )
        return list(reversed(values))
