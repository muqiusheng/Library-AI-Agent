import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.services.profile_fact_extractor import (
    ProfileExtraction,
    ProfileFact,
    normalize_topic,
    validate_fact,
)
from app.services.profile_memory_service import ProfileMemoryService


def fact(source, **changes):
    return ProfileFact.model_validate(
        {
            "category": "foundation",
            "topic": "Python",
            "value_json": json.dumps({"level": "none"}),
            "subject": "user",
            "scope": "persistent",
            "evidence": source,
            "confidence": 0.95,
            **changes,
        }
    )


@pytest.mark.parametrize(
    "topic", ["python", "Python 编程", "Ｐｙｔｈｏｎ", "topic:python", "Python语言"]
)
def test_python_aliases_share_one_key(topic):
    assert normalize_topic(topic) == ("python", "Python")


def test_javascript_is_distinct_and_unmentioned_abilities_are_not_inferred():
    assert normalize_topic("JS") == ("javascript", "JavaScript")
    assert normalize_topic("Java")[0] != normalize_topic("JS")[0]
    assert (
        validate_fact(fact("我没学过 JavaScript", topic="Java"), "我没学过 JavaScript", []) is None
    )


def test_explicit_self_fact_has_canonical_topic_and_self_report_basis():
    result = validate_fact(fact("我没学过 Python", topic="python编程"), "我没学过 Python", [])
    assert result.key == "topic:python"
    assert result.value == {
        "topic": "Python",
        "level": "none",
        "label": "未学习",
        "basis": "self_report",
    }


@pytest.mark.parametrize(
    "text",
    [
        "帮朋友找书，他没学过 Python",
        "我朋友没学过 Python",
        "假设我没学过 Python",
        "如果我没学过 Python，该怎么选书",
        "这次只想找 Python 零基础教材",
        "书里举例说我没学过 Python",
        "我想学 Python",
        "推荐 Python 入门教材",
    ],
)
def test_unreliable_or_nonself_claims_are_rejected_even_if_model_mislabels_them(text):
    assert validate_fact(fact(text), text, []) is None


@pytest.mark.parametrize(
    "changes",
    [
        {"subject": "other"},
        {"subject": "unclear"},
        {"scope": "task"},
        {"scope": "hypothetical"},
        {"scope": "unclear"},
        {"confidence": 0.5},
        {"value_json": "not-json"},
        {"value_json": '{"level":"expert"}'},
        {"value_json": '{"level":"advanced"}'},
        {"topic": "Java"},
    ],
)
def test_candidate_validation_filters_invalid_fact(changes):
    assert validate_fact(fact("我没学过 Python", **changes), "我没学过 Python", []) is None


@pytest.mark.parametrize(
    "history",
    [
        [],
        [{"role": "assistant", "content": "你喜欢 Python 吗？"}],
        [{"role": "assistant", "content": "你朋友学过 Python 吗？"}],
        [{"role": "assistant", "content": "你学过 Python 和 Java 吗？"}],
        [{"role": "assistant", "content": "你学过 Java 吗？"}],
        [
            {"role": "user", "content": "帮朋友找书"},
            {"role": "assistant", "content": "学过 Python 吗？"},
        ],
    ],
)
def test_bare_negative_requires_an_unambiguous_self_ability_question(history):
    assert validate_fact(fact("没有"), "没有", history) is None


def test_bare_negative_is_grounded_in_previous_question():
    history = [{"role": "assistant", "content": "你学过 Python 吗？"}]
    result = validate_fact(fact("没有"), "没有", history)
    assert result.value["topic"] == "Python"
    assert result.value["level"] == "none"


def test_history_fact_cannot_be_reextracted_without_current_evidence():
    history = [{"role": "user", "content": "我没学过 Python"}]
    assert validate_fact(fact("我没学过 Python"), "好的", history) is None


def test_mixed_message_keeps_explicit_self_fact():
    text = "帮朋友找 Java 教材，我没学过 Python"
    assert validate_fact(fact("我没学过 Python"), text, []) is not None


def test_unknown_and_positive_ability_are_distinct_from_none():
    for level, text in [("unknown", "我不确定自己的 Python 基础"), ("basic", "我了解 Python 基础")]:
        result = validate_fact(fact(text, value_json=json.dumps({"level": level})), text, [])
        assert result.value["level"] == level


def test_temporary_preference_is_not_a_long_term_preference():
    for text, accepted in [("这次优先推荐入门书", False), ("以后优先推荐入门书", True)]:
        candidate = fact(text, category="difficulty_preference", value_json='"beginner"')
        assert (validate_fact(candidate, text, []) is not None) == accepted


@pytest.mark.asyncio
async def test_extractor_sends_history_and_filters_candidates_independently():
    text = "我没学过 Python，帮朋友找 Java 教材"
    candidates = [
        fact("我没学过 Python", topic="python编程"),
        fact("帮朋友找 Java 教材", topic="Java", subject="other"),
    ]
    provider = SimpleNamespace(
        available=True, structured=AsyncMock(return_value=ProfileExtraction(facts=candidates))
    )
    service = ProfileMemoryService(MagicMock(), provider)
    history = [{"role": "assistant", "content": "你有哪些编程基础？"}]
    result = await service._extract_async(text, history=history)
    assert len(result) == 1 and result[0].key == "topic:python"
    messages = provider.structured.call_args.args[0]
    assert messages[1] == history[0]
    assert messages[-1] == {"role": "user", "content": text}


@pytest.mark.asyncio
async def test_alias_duplicates_in_one_response_are_not_written_twice():
    text = "我没学过 Python"
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=ProfileExtraction(
                facts=[fact(text, topic="python"), fact(text, topic="Python编程")],
            )
        ),
    )
    result = await ProfileMemoryService(MagicMock(), provider)._extract_async(text)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_unavailable_or_failed_provider_writes_no_fact(caplog):
    provider = SimpleNamespace(available=False, structured=AsyncMock())
    service = ProfileMemoryService(MagicMock(), provider)
    assert await service._extract_async("我没学过 Python") == []
    provider.structured.assert_not_called()
    provider.available = True
    provider.structured.side_effect = RuntimeError("simulated failure")
    assert await service._extract_async("我没学过 Python") == []
    assert "no facts written" in caplog.text


@pytest.mark.parametrize("changes", [{"category": "hobby"}, {"confidence": 2}, {"evidence": ""}])
def test_invalid_schema_is_rejected(changes):
    with pytest.raises(ValidationError):
        fact("我没学过 Python", **changes)


def test_goal_and_preference_values_must_be_grounded_in_current_message():
    text = "我想学 Python"
    assert validate_fact(fact(text, category="learning_goals", value_json='["Python"]'), text, [])
    assert (
        validate_fact(fact(text, category="learning_goals", value_json='["考研"]'), text, [])
        is None
    )
    text = "以后优先推荐进阶书"
    assert (
        validate_fact(
            fact(text, category="difficulty_preference", value_json='"beginner"'), text, []
        )
        is None
    )


@pytest.mark.asyncio
async def test_multiple_goals_and_current_utterance_correction():
    text = "我想学 Python，我准备考研"
    provider = SimpleNamespace(
        available=True,
        structured=AsyncMock(
            return_value=ProfileExtraction(
                facts=[
                    fact("我准备考研", category="learning_goals", value_json='["考研"]'),
                    fact("我想学 Python", category="learning_goals", value_json='["Python"]'),
                ],
            )
        ),
    )
    service = ProfileMemoryService(MagicMock(), provider)
    result = await service._extract_async(text)
    assert set(result[0].value) == {"Python", "考研"}
    text = "我以前没学过 Python，但现在我了解 Python 基础"
    provider.structured.return_value = ProfileExtraction(
        facts=[
            fact("现在我了解 Python 基础", value_json='{"level":"basic"}'),
            fact("我以前没学过 Python"),
        ]
    )
    result = await service._extract_async(text)
    assert len(result) == 1
    assert result[0].value["level"] == "basic"
