import pytest

from app.schemas.conversation import ConstraintRead, LearningNeedState
from app.services.need_policy_service import NeedPolicyService


@pytest.mark.parametrize("values,expected", [
    ({"topic": "机器学习"}, "learning_goal"),
    ({"topic": "高等数学", "scenario": "exam"}, "learning_goal"),
    ({"topic": "客户流失", "scenario": "research", "learning_goal": "论文预测方法"}, "foundation"),
    ({"topic": "小说", "scenario": "interest"}, "learning_goal"),
])
def test_dynamic_high_impact_question(values, expected):
    decision = NeedPolicyService().decide(LearningNeedState(**values))
    assert decision.action == "ask"
    assert decision.question_fields == [expected]


@pytest.mark.parametrize("values", [
    {"topic": "Python", "foundation": "会编程", "learning_goal": "Excel 数据处理"},
    {"topic": "科幻小说", "scenario": "interest"},
    {"topic": "机器学习", "clarification_rounds": 2},
    {"topic": "Python", "asked_fields": ["learning_goal", "foundation", "content_preference",
                                          "language_preference"]},
])
def test_recommend_without_filling_every_preference(values):
    assert NeedPolicyService().decide(LearningNeedState(**values)).action == "recommend"


@pytest.mark.parametrize("status", ["unknown", "skipped", "not_applicable"])
def test_unanswered_goal_is_distinct_but_not_repeated(status):
    state = LearningNeedState(topic="Python", field_status={"learning_goal": status})
    assert state.learning_goal is None
    assert state.field_status["learning_goal"] == status
    assert NeedPolicyService().decide(state).question_fields == ["foundation"]


def test_topic_required_even_with_direct_request_or_exhausted_budget():
    for topic in (None, "推荐几本书", "不限"):
        state = LearningNeedState(topic=topic, clarification_rounds=2)
        assert NeedPolicyService().decide(state, direct=True).question_fields == ["topic"]
    assert NeedPolicyService().decide(state, cancel=True).action == "cancel"


def test_direct_request_and_existing_list_skip_optional_questions():
    state = LearningNeedState(topic="机器学习")
    assert NeedPolicyService().decide(state, direct=True).action == "recommend"
    assert NeedPolicyService().decide(state, refine=True).action == "refine"


def test_old_state_derives_statuses_without_inventing_a_foundation():
    state = LearningNeedState.model_validate({
        "topic": "机器学习", "content_preference": "any",
        "language_preference": "not_applicable", "asked_fields": ["foundation"],
    })
    assert state.field_status["topic"] == "confirmed"
    assert state.field_status["content_preference"] == "any"
    assert state.field_status["language_preference"] == "not_applicable"
    assert state.field_status["foundation"] == "unset"


def test_empty_result_only_suggests_a_proven_blocking_filter():
    conditions = ConstraintRead(only_available=True, difficulty="beginner", excluded_terms=["Java"])
    stats = {"steps": [{"id": "availability", "applied": True, "before": 3, "remaining": 0}]}
    decision = NeedPolicyService.after_recommendation(conditions, stats, has_items=False)
    assert decision.action == "relax"
    assert decision.suggested_changes.model_dump(exclude_unset=True) == {"only_available": False}
    assert conditions.only_available  # A suggestion never mutates the user's conditions.
    for stats in ({}, {"steps": [{"id": "availability", "applied": True,
                                  "before": 0, "remaining": 0}]}):
        decision = NeedPolicyService.after_recommendation(conditions, stats, has_items=False)
        assert decision.suggested_changes is None
        assert "暂未找到" in decision.question
    decision = NeedPolicyService.after_recommendation(conditions, {}, has_items=True)
    assert decision.action == "recommend"
