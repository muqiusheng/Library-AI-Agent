import re

from sqlalchemy.orm import Session

from app.db.models import Conversation, ConversationConstraint
from app.schemas.conversation import ConstraintRead, ConstraintUpdate


class ConversationConstraintService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, conversation: Conversation) -> ConstraintRead:
        values = conversation.constraints.constraints_json if conversation.constraints else {}
        return ConstraintRead.model_validate(values)

    def update(
        self, conversation: Conversation, payload: ConstraintUpdate, *, commit: bool = True
    ) -> ConstraintRead:
        current = (
            dict(conversation.constraints.constraints_json) if conversation.constraints else {}
        )
        for field in payload.model_fields_set:
            value = getattr(payload, field)
            if value is not None or field == "difficulty":
                current[field] = value
        if conversation.constraints is None:
            conversation.constraints = ConversationConstraint(constraints_json=current)
        else:
            conversation.constraints.constraints_json = current
        if commit:
            self.session.commit()
        return ConstraintRead.model_validate(current)

    def update_from_message(
        self,
        conversation: Conversation,
        text: str,
        *,
        only_available: bool | None,
        commit: bool = True,
    ) -> ConstraintRead:
        changes: dict = {}
        if only_available is not None:
            changes["only_available"] = only_available
        if any(
            value in text for value in ("不限可借", "借不到也可以", "不必只看可借", "取消可借限制")
        ):
            changes["only_available"] = False
        elif any(value in text for value in ("只看可借", "在馆可借", "必须可借")):
            changes["only_available"] = True
        if any(value in text for value in ("简单一点", "简单点", "太难", "入门一些")):
            changes["difficulty"] = "beginner"
        elif any(
            value in text
            for value in ("难一点", "进阶一些", "更有挑战", "进阶书", "高级教材", "高级图书")
        ):
            changes["difficulty"] = "advanced"
        if "取消难度" in text or "不限难度" in text:
            changes["difficulty"] = None
        excluded = re.findall(r"(?:不要|排除|不想看)([A-Za-z+#.]{2,20}|[\u4e00-\u9fff]{2,8})", text)
        excluded = [
            value
            for value in excluded
            if not re.match(r"第?[一二三四五六七八九十0-9]+[本个]", value)
        ]
        if excluded:
            current = self.get(conversation).excluded_terms
            changes["excluded_terms"] = list(dict.fromkeys([*current, *excluded]))
        if "取消排除" in text or "不再排除" in text:
            changes["excluded_terms"] = []
        if "取消所有限制" in text or "取消限制" in text:
            changes.update(only_available=False, difficulty=None, excluded_terms=[])
        if not changes:
            return self.get(conversation)
        return self.update(conversation, ConstraintUpdate.model_validate(changes), commit=commit)
