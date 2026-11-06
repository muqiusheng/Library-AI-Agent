import json
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, ConversationConstraint, MessageRole, RecommendationSet, User
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversation import ConstraintRead, ConversationTask
from app.schemas.recommendation import RecommendationSetRead
from app.services.recommendation_service import RecommendationService


@dataclass
class ConversationContext:
    task: ConversationTask
    constraints: ConstraintRead
    history: list[dict[str, str]]
    profile: dict
    recommendation: RecommendationSetRead | None = None

    def prompt(self) -> str:
        return json.dumps(
            {
                "task": self.task.model_dump(mode="json"),
                "constraints": self.constraints.model_dump(),
                "profile": self.profile,
                "books": [item.model_dump(mode="json") for item in self.recommendation.items]
                if self.recommendation
                else [],
            },
            ensure_ascii=False,
        )


class ConversationContextService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build(self, conversation: Conversation, user: User) -> ConversationContext:
        values = conversation.constraints.constraints_json if conversation.constraints else {}
        task = ConversationTask.model_validate(values.get("_task", {}))
        latest = self.session.scalar(
            select(RecommendationSet)
            .where(
                RecommendationSet.conversation_id == conversation.id,
                RecommendationSet.user_id == user.id,
            )
            .order_by(RecommendationSet.created_at.desc(), RecommendationSet.id.desc())
            .limit(1)
        )
        recommendation = (
            RecommendationService(self.session).get_set(latest.id, user.id) if latest else None
        )
        # Existing conversations acquire a task without rewriting their message history.
        if recommendation and not task.request:
            task.request = recommendation.query
            task.topic = recommendation.query
        history = [
            {"role": message.role.value, "content": message.content}
            for message in ConversationRepository(self.session).recent_messages(
                conversation.id, user.id
            )
            if message.role in {MessageRole.USER, MessageRole.ASSISTANT}
        ]
        return ConversationContext(
            task,
            ConstraintRead.model_validate(values),
            history,
            RecommendationService._profile_snapshot(user),
            recommendation,
        )

    def save(
        self, conversation: Conversation, context: ConversationContext, *, commit: bool = True
    ) -> None:
        values = dict(conversation.constraints.constraints_json) if conversation.constraints else {}
        values.update(context.constraints.model_dump())
        values["_task"] = context.task.model_dump(mode="json")
        if conversation.constraints is None:
            conversation.constraints = ConversationConstraint(constraints_json=values)
        else:
            conversation.constraints.constraints_json = values
        if commit:
            self.session.commit()
