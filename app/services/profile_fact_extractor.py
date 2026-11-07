"""Validate self-reported profile facts without inferring unmentioned abilities."""

import json
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError


class ProfileFact(BaseModel):
    operation: Literal["set", "add", "remove"] = "add"
    category: Literal[
        "foundation", "learning_goals", "interests", "difficulty_preference", "major", "grade"
    ]
    topic: str = Field(default="", max_length=100, description="能力知识点；其他类别可为空")
    value_json: str = Field(max_length=4000, description="事实值的合法 JSON 字符串")
    subject: Literal["user", "other", "unclear"]
    scope: Literal["persistent", "task", "hypothetical", "unclear"]
    evidence: str = Field(min_length=1, max_length=1000, description="当前用户消息中的原文依据")
    confidence: float = Field(ge=0, le=1)


class ProfileExtraction(BaseModel):
    facts: list[ProfileFact] = Field(default_factory=list, max_length=20)


class FoundationValue(BaseModel):
    level: Literal["none", "basic", "intermediate", "advanced", "unknown"]


@dataclass(frozen=True)
class ExtractedMemory:
    category: str
    key: str
    value: dict[str, Any] | list[Any] | str | int | float | bool
    confidence: float
    operation: str = "set"


# Keep identity distinctions: JavaScript is not Java, and AI Agent is not a network proxy.
_ALIASES = {
    "python": ("Python", ("python", "python编程", "python语言", "py语言")),
    "java": ("Java", ("java", "java编程", "java语言")),
    "javascript": ("JavaScript", ("javascript", "js", "javascript编程")),
    "cpp": ("C++", ("c++", "cpp", "c++编程")),
    "machine_learning": ("机器学习", ("机器学习", "machinelearning", "ml")),
    "deep_learning": ("深度学习", ("深度学习", "deeplearning")),
    "database": ("数据库", ("数据库", "数据库基础", "database", "databases")),
    "data_structures": ("数据结构", ("数据结构", "datastructures")),
    "langchain": ("LangChain", ("langchain", "langchain框架")),
}
_LABELS = {
    "none": "未学习",
    "basic": "基础水平",
    "intermediate": "中等水平",
    "advanced": "进阶水平",
    "unknown": "尚不确定",
}
_OTHER = re.compile(
    r"朋友|同学|同事|室友|同伴|弟弟|妹妹|哥哥|姐姐|他|她|friend|classmate|\b(?:he|she|they|his|her|their)\b",
    re.I,
)
_HYPOTHESIS = re.compile(r"假如|假设|如果|要是|举例|例如|他说|她说|题目中|suppose|if\s+i\b", re.I)
_TEMPORARY = re.compile(r"这次|本次|今天先|暂时|本轮|这回|this\s+time|for\s+now", re.I)
_ABILITY = re.compile(
    r"没学过|没接触过|不会|不懂|零基础|学过|掌握|熟悉|精通|熟练|了解|基础|"
    r"会用|会写|能独立|独立完成|不确定|不清楚|know|learned|studied|proficient|beginner",
    re.I,
)
_SHORT_NEGATIVE = {"没有", "没学过", "不会", "不懂", "还没有", "没接触过", "no"}
_SHORT_POSITIVE = {"学过", "会一点", "了解一点", "有一点基础", "yes"}


def normalize_topic(topic: str) -> tuple[str, str]:
    token = re.sub(r"\s+", "", unicodedata.normalize("NFKC", topic)).casefold()
    token = token.removeprefix("topic:")
    for key, (label, aliases) in _ALIASES.items():
        if token == key or token in aliases:
            return key, label
    # Unknown topics remain distinct and do not get collapsed to a broad field.
    return token, unicodedata.normalize("NFKC", topic).strip()


def explicit_foundation(text: str) -> list[dict]:
    """Read only explicitly named levels from a manually edited foundation field."""
    facts = []
    for clause in re.split(r"[，,。；;]|但是|但", text):
        level = None
        if re.search(r"没学过|没接触过|零基础|不会|不懂|没有.*基础", clause):
            level = "none"
        elif re.search(r"熟练|精通|进阶|高级|独立完成", clause):
            level = "advanced"
        elif re.search(r"熟悉|中级|中等", clause):
            level = "intermediate"
        elif re.search(r"学过|基础|入门|了解|会用|会写", clause):
            level = "basic"
        if level:
            for _, (label, _) in _ALIASES.items():
                if _has_topic(label, clause):
                    facts.append({"topic": label, "level": level, "basis": "self_report"})
    return facts


def _clause(text: str, evidence: str) -> str:
    start = text.find(evidence)
    marks = (*"，,。；;！？!?\n", "但", "不过")
    positions = [(text.rfind(mark, 0, start), len(mark)) for mark in marks]
    left = max((position + size - 1 for position, size in positions if position >= 0), default=-1)
    ends = [text.find(mark, start + len(evidence)) for mark in marks]
    right = min((value for value in ends if value >= 0), default=len(text))
    return text[left + 1 : right]


def _has_topic(topic: str, text: str) -> bool:
    key, label = normalize_topic(topic)
    aliases = _ALIASES.get(key, (label, (label,)))[1]
    compact = unicodedata.normalize("NFKC", text).casefold()
    return any(
        re.search(
            r"(?<![a-z0-9])"
            + re.escape(alias)
            .replace("machinelearning", r"machine\s*learning")
            .replace("deeplearning", r"deep\s*learning")
            .replace("datastructures", r"data\s*structures")
            + r"(?![a-z0-9])",
            compact,
        )
        for alias in aliases
    )


def _question_supports(topic: str, history: list[dict[str, str]]) -> bool:
    if not history or history[-1]["role"] != "assistant":
        return False
    question = history[-1]["content"]
    if _OTHER.search(question) or _HYPOTHESIS.search(question):
        return False
    if not re.search(r"学过|掌握|基础|熟悉|会|know|studied|learned", question, re.I):
        return False
    # An unresolved multi-topic question cannot ground a bare yes/no answer.
    if re.search(r"还是|以及|和|、|\bor\b|\band\b", question, re.I):
        return False
    supported = _has_topic(topic, question)
    preceding_user = next((m["content"] for m in reversed(history[:-1]) if m["role"] == "user"), "")
    if _OTHER.search(preceding_user) and not re.search(
        r"(?:我|本人)(?:自己)?(?:没|已|学|会|的基础)", preceding_user
    ):
        return False
    return supported


def validate_fact(
    fact: ProfileFact, text: str, history: list[dict[str, str]]
) -> ExtractedMemory | None:
    if fact.subject != "user" or fact.scope != "persistent" or fact.confidence < 0.75:
        return None
    if fact.evidence not in text:
        return None
    clause = _clause(text, fact.evidence)
    if _OTHER.search(clause) or _HYPOTHESIS.search(clause) or _TEMPORARY.search(clause):
        return None
    # Continuations inherit the subject unless the speaker explicitly switches to self.
    prefix = text[: text.find(fact.evidence)]
    explicit_self = re.search(r"我|本人|\bi\b|\bmy\b", clause, re.I)
    if not explicit_self and (_OTHER.search(prefix) or _HYPOTHESIS.search(prefix)):
        return None
    sentence_prefix = re.split(r"[。；;！？!?\n]", prefix)[-1]
    if _HYPOTHESIS.search(sentence_prefix):
        return None
    try:
        value = json.loads(fact.value_json)
    except (ValueError, TypeError):
        return None
    if fact.category == "foundation":
        topic = fact.topic or (value.get("topic", "") if isinstance(value, dict) else "")
        if not isinstance(topic, str) or not topic.strip():
            return None
        key, label = normalize_topic(topic)
        if not key or len(key) > 94:
            return None
        try:
            foundation = FoundationValue.model_validate(value)
        except ValidationError:
            return None
        short = text.strip(" 。！？!?\n").casefold()
        if short in _SHORT_NEGATIVE | _SHORT_POSITIVE:
            if not _question_supports(topic, history):
                return None
            if short in _SHORT_NEGATIVE and foundation.level != "none":
                return None
            if short in _SHORT_POSITIVE and foundation.level not in {"basic", "unknown"}:
                return None
        elif not _ABILITY.search(clause) or not _has_topic(topic, clause):
            return None
        # Explicit lack of experience must never become a positive ability score.
        if re.search(r"没学过|没接触过|零基础|不会|不懂", clause) and foundation.level != "none":
            return None
        value = {
            "topic": label,
            "level": foundation.level,
            "label": _LABELS[foundation.level],
            "basis": "self_report",
        }
        return ExtractedMemory("foundation", f"topic:{key}", value, fact.confidence)
    if fact.category == "difficulty_preference":
        if not isinstance(value, str) or value not in {
            "beginner",
            "progressive",
            "intermediate",
            "advanced",
        }:
            return None
        if not re.search(r"以后|长期|一直|通常|习惯|偏好|优先|prefer|always", clause, re.I):
            return None
        markers = {
            "beginner": r"入门|基础|简单|beginner",
            "progressive": r"循序|渐进|progressive",
            "intermediate": r"中等|中级|intermediate",
            "advanced": r"进阶|高级|挑战|更难|advanced",
        }
        if not re.search(markers[value], clause, re.I):
            return None
    elif fact.category in {"learning_goals", "interests"}:
        if isinstance(value, str):
            value = [value.strip()]
        if (
            not isinstance(value, list)
            or not value
            or not all(
                isinstance(item, str) and item.strip() and len(item) <= 200 for item in value
            )
        ):
            return None
        if fact.category == "interests" and not re.search(
            r"喜欢|感兴趣|爱好|兴趣|like|interest", clause, re.I
        ):
            return None
        for item in value:
            topic = re.sub(r"^(?:希望学习|学习|想学|准备|计划)", "", item.strip())
            if not topic or not _has_topic(topic, clause):
                return None
        if fact.category == "learning_goals" and not re.search(
            r"想学|学习目标|准备|计划|考研|希望学|目标|want|plan", clause, re.I
        ):
            return None
    else:
        if not isinstance(value, str) or not value.strip() or len(value) > 150:
            return None
        field_question = "专业|主修" if fact.category == "major" else "年级|大几|几年级"
        direct = re.search(r"我|本人", clause) and (
            re.search(r"专业|主修|学的是|读的是", clause)
            if fact.category == "major"
            else re.search(r"大[一二三四五]|研[一二三]|博士|年级|[1-9]年级", clause)
        )
        reply = (
            history
            and history[-1]["role"] == "assistant"
            and re.search(field_question, history[-1]["content"])
            and not (
                _OTHER.search(history[-1]["content"]) or _HYPOTHESIS.search(history[-1]["content"])
            )
        )
        if not (direct or reply) or value not in clause:
            return None
    operation = "set"
    if fact.category in {"learning_goals", "interests"}:
        operation = fact.operation
        if re.search(r"不再|不喜欢|不感兴趣|放弃|取消.*目标", clause):
            operation = "remove"
        elif re.search(r"改为|改成|只喜欢|只对", clause):
            operation = "set"
    return ExtractedMemory(fact.category, fact.category, value, fact.confidence, operation)
