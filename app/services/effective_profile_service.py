from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Conversation, Message, ProfileMemory, User
from app.repositories.profile_repository import ProfileRepository
from app.services.profile_fact_extractor import _has_topic, explicit_foundation, normalize_topic

_FIELDS = {"grade", "major", "learning_goals", "interests", "difficulty_preference"}
_LEVELS = {"none", "basic", "intermediate", "advanced", "unknown"}


def normalize_fact(category: str, key: str, value: Any) -> tuple[str, str, Any]:
    if category == "profile" and key == "foundation":
        if not isinstance(value, str) or not value.strip() or len(value) > 2000:
            raise ValueError("现有基础必须是非空文本")
    if category == "profile" and key in _FIELDS:
        category = key
    if category == "interest":
        category = "interests"
    if category == "foundation":
        if not isinstance(value, dict):
            raise ValueError("能力事实需要包含知识点和水平")
        topic = value.get("topic") or key.removeprefix("topic:")
        canonical, label = normalize_topic(topic)
        level = {"beginner": "basic"}.get(value.get("level"), value.get("level"))
        if not canonical or len(canonical) > 94 or level not in _LEVELS:
            raise ValueError("无效的知识点或能力水平")
        value = {"topic": label, "level": level, "basis": value.get("basis", "self_report")}
        category, key = "foundation", f"topic:{canonical}"
    elif category in _FIELDS:
        key = category
        if category in {"interests", "learning_goals"}:
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError("目标和兴趣必须是字符串数组")
            normalized = [normalize_topic(item.strip())[1] for item in value if item.strip()]
            value = list({item.casefold(): item for item in normalized}.values())
        elif category == "difficulty_preference":
            if value not in {"beginner", "progressive", "intermediate", "advanced"}:
                raise ValueError("无效的难度偏好")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError("画像字段不能为空")
    return category, key, value


def revision_time(memory: ProfileMemory) -> datetime:
    value = memory.created_at
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


class EffectiveProfileService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def revisions(self, user_id) -> dict[tuple[str, str], list[ProfileMemory]]:
        groups: dict[tuple[str, str], list[ProfileMemory]] = {}
        for memory in ProfileRepository(self.session).list_memories(user_id, include_inactive=True):
            try:
                category, key, _ = normalize_fact(memory.category, memory.key, memory.value_json)
            except (ValueError, TypeError, AttributeError):
                continue
            groups.setdefault((category, key), []).append(memory)
        for values in groups.values():
            values.sort(key=lambda m: (revision_time(m), str(m.id)), reverse=True)
        return groups

    def winners(self, user_id) -> dict[tuple[str, str], ProfileMemory]:
        result = {}
        for identity, revisions in self.revisions(user_id).items():
            # A removed newest revision must not revive an older alias or version.
            if not revisions[0].is_active:
                continue
            active = [
                memory
                for memory in revisions
                if memory.is_active and (memory.is_user_edited or memory.confidence >= 0.75)
            ]
            if not active:
                continue
            manual = [memory for memory in active if memory.is_user_edited]
            result[identity] = (manual or active)[0]
        return result

    def build(self, user: User) -> dict:
        base = user.profile
        profile = {
            "grade": base.grade if base else "",
            "major": base.major if base else "",
            "foundation": base.foundation if base else "",
            "learning_goals": list(base.learning_goals) if base else [],
            "interests": list(base.interests) if base else [],
            "difficulty_preference": base.difficulty_preference.value if base else "progressive",
            "abilities": {},
            "sources": {},
        }
        if base:
            timestamp = base.updated_at
            timestamp = timestamp.replace(tzinfo=UTC) if timestamp.tzinfo is None else timestamp
            for field in [*_FIELDS, "foundation"]:
                value = profile[field]
                profile["sources"][field] = {
                    "memory_id": "",
                    "source": "registration",
                    "source_message_id": None,
                    "is_user_edited": False,
                    "confidence": 1.0,
                    "updated_at": timestamp.isoformat(),
                    "evidence": "、".join(value) if isinstance(value, list) else value,
                }
        for ability in explicit_foundation(profile["foundation"]):
            key, _ = normalize_topic(ability["topic"])
            profile["abilities"][key] = ability
            profile["sources"][f"topic:{key}"] = profile["sources"]["foundation"]
        winners = self.winners(user.id)
        message_ids = {
            memory.source_message_id
            for memory in winners.values()
            if memory.source_message_id is not None
        }
        evidence = (
            dict(
                self.session.execute(
                    select(Message.id, Message.content)
                    .join(Conversation, Message.conversation_id == Conversation.id)
                    .where(Message.id.in_(message_ids), Conversation.user_id == user.id)
                ).all()
            )
            if message_ids
            else {}
        )
        manual_foundation = winners.get(("profile", "foundation"))
        if manual_foundation and isinstance(manual_foundation.value_json, str):
            profile["foundation"] = manual_foundation.value_json
            profile["abilities"] = {}
            profile["sources"] = {
                key: value
                for key, value in profile["sources"].items()
                if not key.startswith("topic:")
            }
            for ability in explicit_foundation(profile["foundation"]):
                key, _ = normalize_topic(ability["topic"])
                profile["abilities"][key] = ability
        for (category, key), memory in winners.items():
            _, _, value = normalize_fact(memory.category, memory.key, memory.value_json)
            source = {
                "memory_id": str(memory.id),
                "source": memory.source.value,
                "source_message_id": str(memory.source_message_id)
                if memory.source_message_id
                else None,
                "is_user_edited": memory.is_user_edited,
                "confidence": memory.confidence,
                "updated_at": revision_time(memory).isoformat(),
                "evidence": evidence.get(memory.source_message_id),
            }
            if category == "foundation":
                if manual_foundation and revision_time(memory) < revision_time(manual_foundation):
                    continue
                profile["abilities"][key.removeprefix("topic:")] = value
                profile["sources"][key] = source
            elif category in _FIELDS:
                profile[category] = value
                profile["sources"][category] = source
            elif category == "profile" and key == "foundation":
                profile["sources"]["foundation"] = source
                for ability_key in profile["abilities"]:
                    profile["sources"].setdefault(f"topic:{ability_key}", source)
        if profile["abilities"]:
            profile["foundation_background"] = profile["foundation"]
            profile["foundation"] = "；".join(
                f"{value['topic']}: {value['level']}" for value in profile["abilities"].values()
            )
        return profile

    @staticmethod
    def relevant_abilities(profile: dict, query: str) -> list[dict]:
        # A small explicit prerequisite map; it does not rewrite the requested topic.
        prerequisites = {"langchain": ["python"], "深度学习": ["machine_learning"]}
        related = set()
        for term, topics in prerequisites.items():
            if term in query.casefold():
                related.update(topics)
        return [
            value
            for key, value in profile.get("abilities", {}).items()
            if key in related or _has_topic(value["topic"], query)
        ]
