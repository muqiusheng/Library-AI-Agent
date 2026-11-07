"""Public execution summaries backed by actual pipeline events."""

from copy import deepcopy
from time import perf_counter
from typing import Any

from app.services.effective_profile_service import EffectiveProfileService

PROFILE_FIELDS = {"learning_goals", "interests", "major", "difficulty_preference"}


def exclude_profile_facts(profile: dict, keys: list[str]) -> dict:
    """Mask facts in every profile representation used by search, ranking and summary."""
    result = deepcopy(profile)
    for key in keys:
        if key.startswith("topic:"):
            result.get("abilities", {}).pop(key.removeprefix("topic:"), None)
        elif key in PROFILE_FIELDS:
            result[key] = (
                []
                if key in {"learning_goals", "interests"}
                else "progressive"
                if key == "difficulty_preference"
                else ""
            )
        result.get("sources", {}).pop(key, None)
    if keys:
        # Original sentences can mention multiple facts. Do not feed excluded facts
        # back to the model through background text or source quotations.
        result.pop("foundation_background", None)
        result["foundation"] = "；".join(
            f"{item['topic']}: {item['level']}" for item in result.get("abilities", {}).values()
        )
        result.get("sources", {}).pop("foundation", None)
        for source in result.get("sources", {}).values():
            source.pop("evidence", None)
        result["excluded_profile_keys"] = list(keys)
    return result


class RecommendationProgress:
    def __init__(self, turn_id: str | None = None) -> None:
        self.started = perf_counter()
        self.stage_started = self.started
        self.steps: list[dict[str, Any]] = []
        self.evidence: list[dict[str, Any]] = []
        self.comparisons: list[dict[str, Any]] = []
        self.summary = ""
        self.status = "running"
        self.elapsed_ms = 0
        self.extra: dict[str, Any] = {"turn_id": turn_id}

    def resume(self, previous: dict, stage: str) -> None:
        boundaries = {
            "retrieving": "retrieving",
            "comparing": "filtering",
            "generating": "generating",
        }
        for step in previous.get("steps", []):
            if step["id"] == boundaries[stage] or step["status"] != "complete":
                break
            self.steps.append(
                {
                    **deepcopy(step),
                    "reused": True,
                    "previous_elapsed_ms": step.get("previous_elapsed_ms", step["elapsed_ms"]),
                    "elapsed_ms": 0,
                }
            )
        self.extra.update(
            {
                key: deepcopy(previous[key])
                for key in (
                    "filter_stats",
                    "candidates",
                    "excluded_profile_keys",
                    "excluded_profile_evidence",
                )
                if key in previous
            }
        )
        self.evidence = deepcopy(previous.get("profile_evidence", []))
        self.comparisons = deepcopy(previous.get("comparisons", []))
        self.summary = previous.get("summary", "")
        if stage != "generating":
            self.comparisons = []
            self.summary = ""
            self.extra.pop("candidates", None)
            if stage == "retrieving":
                self.extra.pop("filter_stats", None)
        self.extra["retry_from"] = stage

    def update(self, event: dict) -> dict:
        now = perf_counter()
        if event.get("stage"):
            if self.steps and self.steps[-1]["status"] == "running":
                self.steps[-1]["status"] = "complete"
                self.steps[-1]["elapsed_ms"] = round((now - self.stage_started) * 1000)
            self.stage_started = now
            self.steps.append(
                {
                    "id": event["stage"],
                    "label": event["label"],
                    "detail": event.get("detail", ""),
                    "status": "running",
                    "elapsed_ms": 0,
                }
            )
        elif "detail" in event and self.steps:
            self.steps[-1]["detail"] = event["detail"]
        if "profile_evidence" in event:
            self.evidence = event["profile_evidence"]
        if "comparisons" in event:
            self.comparisons = event["comparisons"]
        if "summary" in event:
            self.summary = event["summary"]
        for key in (
            "filter_stats",
            "candidates",
            "excluded_profile_keys",
            "excluded_profile_evidence",
            "retry_stages",
            "retry_note",
            "error_message",
        ):
            if key in event:
                self.extra[key] = deepcopy(event[key])
        return self.snapshot()

    def snapshot(self) -> dict:
        steps = deepcopy(self.steps)
        elapsed = self.elapsed_ms
        if self.status == "running":
            now = perf_counter()
            elapsed = round((now - self.started) * 1000)
            if steps and steps[-1]["status"] == "running":
                steps[-1]["elapsed_ms"] = round((now - self.stage_started) * 1000)
        return {
            **deepcopy(self.extra),
            "status": self.status,
            "elapsed_ms": elapsed,
            "steps": steps,
            "profile_evidence": deepcopy(self.evidence),
            "comparisons": deepcopy(self.comparisons),
            "summary": self.summary,
        }

    def finish(self, status: str = "complete") -> dict:
        current = self.snapshot()
        self.steps = current["steps"]
        self.elapsed_ms = current["elapsed_ms"]
        if self.steps:
            self.steps[-1]["status"] = status
        self.status = status
        return self.snapshot()


def profile_evidence(
    profile: dict, query: str, current_message_id: str | None = None
) -> list[dict]:
    """Expose relevant supplied facts, preserving their level and original source."""
    items = []
    sources = profile.get("sources", {})

    def add(key: str, label: str, value: str, usage: str) -> None:
        if not value:
            return
        source = sources.get(key, {})
        same_message = bool(current_message_id) and (
            source.get("source_message_id") == current_message_id
        )
        source_kind = source.get("source", "")
        source_label = (
            "本次输入"
            if same_message
            else {
                "registration": "注册资料",
                "manual": "手工确认",
                "conversation": "历史对话",
                "feedback": "阅读反馈",
            }.get(source_kind, "来源未记录")
        )
        nature = "用户提供"
        if source_kind == "conversation" and not source.get("is_user_edited"):
            nature = "从用户陈述提取"
        elif source_kind == "feedback":
            nature = "行为记录"
        items.append(
            {
                "key": key,
                "value_json": deepcopy(
                    profile.get("abilities", {}).get(key.removeprefix("topic:"))
                    if key.startswith("topic:")
                    else profile.get(key)
                ),
                "label": label,
                "value": value,
                "usage": usage,
                "source_label": source_label,
                "nature": nature,
                "source_message_id": source.get("source_message_id"),
                "updated_at": source.get("updated_at"),
                "evidence": source.get("evidence") or "",
            }
        )

    levels = {
        "none": "未学习",
        "basic": "有基础（熟练程度未确认）",
        "intermediate": "中等水平",
        "advanced": "进阶水平",
        "unknown": "水平尚不确定",
    }
    related = EffectiveProfileService.relevant_abilities(profile, query)
    for key, ability in profile.get("abilities", {}).items():
        if ability in related:
            add(
                f"topic:{key}",
                "学习基础",
                f"{ability['topic']}：{levels.get(ability['level'], '水平尚不确定')}",
                "作为学习基础与难度选择的参考",
            )
    for key, label, usage in (
        ("learning_goals", "学习目标", "用于检索方向与目标匹配"),
        ("interests", "兴趣方向", "作为内容偏好的参考"),
        ("major", "专业背景", "作为专业相关性的参考"),
        ("difficulty_preference", "难度偏好", "作为难度初筛参考，本次明确要求优先"),
    ):
        value = profile.get(key)
        if key == "difficulty_preference":
            # A system default is not a user-provided preference.
            if key not in sources:
                continue
            value = {
                "beginner": "轻松入门",
                "progressive": "循序渐进",
                "intermediate": "有一定挑战",
                "advanced": "偏进阶",
            }.get(value, "")
        if value:
            add(key, label, "、".join(value) if isinstance(value, list) else value, usage)
    return items
