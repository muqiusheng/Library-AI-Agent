import re

from sqlalchemy.orm import Session

from app.db.models import Conversation, ConversationConstraint
from app.schemas.conversation import (
    ConstraintRead,
    ConstraintUpdate,
    LearningNeedState,
)


class ConversationConstraintService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _raw_values(conversation: Conversation) -> dict:
        if conversation.constraints is None:
            return {}

        return dict(
            conversation.constraints.constraints_json or {}
        )

    @staticmethod
    def _assign(
        conversation: Conversation,
        values: dict,
    ) -> None:
        if conversation.constraints is None:
            conversation.constraints = ConversationConstraint(
                constraints_json=values
            )
        else:
            conversation.constraints.constraints_json = values

    def get(self, conversation: Conversation) -> ConstraintRead:
        return ConstraintRead.model_validate(
            self._raw_values(conversation)
        )

    def update(
        self,
        conversation: Conversation,
        payload: ConstraintUpdate,
        *,
        commit: bool = True,
    ) -> ConstraintRead:
        current = self._raw_values(conversation)

        for field in payload.model_fields_set:
            value = getattr(payload, field)

            if value is not None:
                current[field] = value

        self._assign(conversation, current)

        if commit:
            self.session.commit()

        return ConstraintRead.model_validate(current)

    def save_learning_need(
        self,
        conversation: Conversation,
        state: LearningNeedState,
    ) -> None:
        current = self._raw_values(conversation)

        current["learning_need"] = state.model_dump(
            mode="json"
        )

        self._assign(conversation, current)
        self.session.commit()

    def update_from_message(
        self,
        conversation: Conversation,
        text: str,
        *,
        only_available: bool,
    ) -> ConstraintRead:
        changes: dict = {}

        if only_available or any(
            value in text
            for value in (
                "只看可借",
                "在馆可借",
                "必须可借",
            )
        ):
            changes["only_available"] = True

        elif any(
            value in text
            for value in (
                "不限可借",
                "借不到也可以",
            )
        ):
            changes["only_available"] = False

        if any(
            value in text
            for value in (
                "简单一点",
                "简单点",
                "太难",
                "入门一些",
            )
        ):
            changes["difficulty"] = "beginner"

        elif any(
            value in text
            for value in (
                "难一点",
                "进阶一些",
                "更有挑战",
            )
        ):
            changes["difficulty"] = "advanced"

        excluded = re.findall(
            r"(?:不要|排除|不想看)"
            r"([A-Za-z+#.]{2,20}|[\u4e00-\u9fff]{2,8})",
            text,
        )

        if excluded:
            current = self.get(conversation).excluded_terms

            changes["excluded_terms"] = list(
                dict.fromkeys([*current, *excluded])
            )[:20]

        if not changes:
            return self.get(conversation)

        return self.update(
            conversation,
            ConstraintUpdate.model_validate(changes),
        )