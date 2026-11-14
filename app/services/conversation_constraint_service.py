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
        only_available: bool | None = None,
    ) -> ConstraintRead:
        changes: dict = {}

        # 先判断否定表达，避免“不必只看可借”
        # 被其中的“只看可借”误判。
        cancel_availability = any(
            phrase in text
            for phrase in (
                "不必只看可借",
                "不用只看可借",
                "不只看可借",
                "不限可借",
                "借不到也可以",
                "不可借也可以",
                "取消可借限制",
                "取消只看可借",
                "不要求在馆可借",
            )
        )

        require_availability = any(
            phrase in text
            for phrase in (
                "只看可借",
                "只要可借",
                "在馆可借",
                "必须可借",
                "仅推荐可借",
            )
        )

        # 明确的文字要求优先于页面开关。
        if cancel_availability:
            changes["only_available"] = False
        elif require_availability:
            changes["only_available"] = True
        elif only_available is not None:
            changes["only_available"] = only_available

        # 更新难度偏好。
        if any(
            phrase in text
            for phrase in (
                "简单一点",
                "简单点",
                "太难",
                "入门一些",
            )
        ):
            changes["difficulty"] = "beginner"

        elif any(
            phrase in text
            for phrase in (
                "难一点",
                "进阶一些",
                "更有挑战",
            )
        ):
            changes["difficulty"] = "advanced"

        # 保留现有的排除关键词提取逻辑。
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

        # 本轮未改变条件时，返回原有条件。
        if not changes:
            return self.get(conversation)

        return self.update(
            conversation,
            ConstraintUpdate.model_validate(changes),
        )