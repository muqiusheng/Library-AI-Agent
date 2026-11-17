"""Deterministic next-action policy for conversational book selection."""

from dataclasses import dataclass, field
from typing import Literal

from app.schemas.conversation import (
    ConstraintRead,
    ConstraintUpdate,
    LearningNeedState,
    NeedField,
    NeedScenario,
)

GENERIC_TOPICS = {"书", "图书", "好书", "推荐", "推荐几本书", "随便", "不限", "不知道"}
PROGRAMMING_TOPICS = ("数据挖掘", "机器学习", "深度学习", "人工智能", "数据分析", "python", "编程")


@dataclass
class NeedDecision:
    action: Literal["ask", "recommend", "refine", "relax", "cancel"]
    reason: str
    question_fields: list[NeedField] = field(default_factory=list)
    question: str | None = None
    suggested_changes: ConstraintUpdate | None = None


class NeedPolicyService:
    MAX_ROUNDS = 2

    @staticmethod
    def scenario(state: LearningNeedState) -> NeedScenario:
        if state.scenario != "general":
            return state.scenario
        if not state.topic and not state.learning_goal:
            return "general"
        text = f"{state.topic or ''} {state.learning_goal or ''}".casefold()
        for scenario, words in (
            ("exam", ("考试", "考研", "备考", "课程", "四六级")),
            ("research", ("论文", "项目", "研究", "预测", "开发", "毕业设计")),
            ("interest", ("小说", "散文", "诗歌", "文学", "兴趣阅读")),
        ):
            if any(word in text for word in words):
                return scenario
        return "learning"

    def decide(
        self, state: LearningNeedState, *, direct: bool = False,
        cancel: bool = False, refine: bool = False,
    ) -> NeedDecision:
        if cancel:
            return NeedDecision("cancel", "user_cancelled")
        if refine:
            return NeedDecision("refine", "existing_list_adjustment")
        topic = (state.topic or "").strip().strip("。！？?! ")
        if not topic or topic in GENERIC_TOPICS:
            return NeedDecision("ask", "missing_topic", ["topic"])
        if direct:
            return NeedDecision("recommend", "user_requested_recommendation")
        if state.clarification_rounds >= self.MAX_ROUNDS:
            return NeedDecision("recommend", "question_budget_reached")

        scenario = self.scenario(state)
        # A task and an explicit level are enough; optional style slots need not be filled.
        if state.learning_goal and (state.foundation or scenario == "interest"):
            return NeedDecision("recommend", "actionable_need")
        fields: list[NeedField] = ["learning_goal"]
        if scenario != "interest":
            fields.append("foundation")
        elif topic not in {"小说", "文学", "散文", "诗歌", "兴趣阅读"}:
            fields = []
        if scenario != "interest":
            fields.append("content_preference")
        if any(term in topic.casefold() for term in PROGRAMMING_TOPICS):
            fields.append("language_preference")
        if state.foundation and any(
            word in state.foundation for word in ("零基础", "没学过", "没有基础", "基础薄弱")
        ):
            fields.append("basics_preference")
        for name in fields:
            if state.field_status.get(name, "unset") == "unset" and name not in state.asked_fields:
                return NeedDecision("ask", "high_impact_missing_field", [name])
        return NeedDecision("recommend", "no_useful_question")

    @staticmethod
    def after_recommendation(
        constraints: ConstraintRead, stats: dict, *, has_items: bool,
    ) -> NeedDecision:
        if has_items:
            return NeedDecision("recommend", "results_available")
        # Only name a blocking condition when a real filter step emptied the pool.
        availability_blocked = any(
            step.get("id") == "availability" and step.get("applied")
            and step.get("before", 0) > 0 and step.get("remaining") == 0
            for step in stats.get("steps", [])
        )
        if constraints.only_available and availability_blocked:
            return NeedDecision(
                "relax", "availability_removed_remaining_candidates",
                question="本轮剩余候选都因“只看可借”被筛除。是否取消这一限制，查看其他条件不变的书单？",
                suggested_changes=ConstraintUpdate(only_available=False),
            )
        return NeedDecision(
            "relax", "no_matching_candidates",
            question="本轮候选中暂未找到符合需求的图书。你可以补充具体用途，或说明希望调整哪项筛选条件。",
        )
