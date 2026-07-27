from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, MessageRole, MessageType, User
from app.repositories.conversation_repository import ConversationRepository


class ConversationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ConversationRepository(session)

    def create(self, user: User, title: str) -> Conversation:
        conversation = Conversation(user_id=user.id, title=title.strip() or "新会话")
        self.session.add(conversation)
        self.session.commit()
        return conversation

    def update(
        self,
        conversation_id: UUID,
        user: User,
        *,
        title: str | None,
        archived: bool | None,
    ) -> Conversation:
        conversation = self.repository.get_owned(conversation_id, user.id)
        if title is not None:
            conversation.title = title.strip()
        if archived is not None:
            conversation.archived_at = datetime.now(UTC) if archived else None
        self.repository.touch(conversation)
        self.session.commit()
        return conversation

    def delete(self, conversation_id: UUID, user: User) -> None:
        conversation = self.repository.get_owned(conversation_id, user.id)
        self.session.delete(conversation)
        self.session.commit()

    def add_user_message(self, conversation: Conversation, content: str) -> Message:
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=content,
            message_type=MessageType.TEXT,
        )
        self.session.add(message)
        if conversation.title == "新会话":
            conversation.title = content[:36]
        self.repository.touch(conversation)
        self.session.commit()
        return message

    def add_recommendation_message(
        self,
        conversation: Conversation,
        content: str,
        recommendation_set_id: UUID,
    ) -> Message:
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=content,
            message_type=MessageType.RECOMMENDATION,
            structured_payload={"recommendation_set_id": str(recommendation_set_id)},
        )
        self.session.add(message)
        self.repository.touch(conversation)
        self.session.commit()
        return message

    def add_assistant_message(self, conversation: Conversation, content: str) -> Message:
        message = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=content,
            message_type=MessageType.TEXT,
        )
        self.session.add(message)
        self.repository.touch(conversation)
        self.session.commit()
        return message
