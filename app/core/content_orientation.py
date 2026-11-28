"""Dataset-backed book orientation and reader-preference matching."""

from typing import Literal

ContentOrientation = Literal["theory", "balanced", "practice"]

ORIENTATION_LABELS = {
    "theory": "偏理论",
    "balanced": "理论实践结合",
    "practice": "偏实践",
}

BASE_WEIGHTS = {
    "goal": 0.30,
    "difficulty": 0.20,
    "major": 0.15,
    "interest": 0.10,
    "semantic": 0.15,
    "availability": 0.10,
}


def parse_orientation(value: str | None) -> str | None:
    value = (value or "").strip()
    if not value:
        return None
    if value in ORIENTATION_LABELS:
        return value
    for code, label in ORIENTATION_LABELS.items():
        if value == label:
            return code
    raise ValueError(f"无效的内容取向：{value}")


def orientation_score(preference: str | None, actual: str | None) -> float | None:
    if preference not in ORIENTATION_LABELS or actual not in ORIENTATION_LABELS:
        return None
    if preference == actual:
        return 100.0
    if "balanced" in (preference, actual):
        return 70.0
    return 30.0


def recommendation_weights(weights: dict[str, float] | None = None) -> dict[str, float]:
    """Extend stored six-dimensional weights without discarding custom proportions."""
    result = dict(weights or BASE_WEIGHTS)
    if "orientation" not in result:
        result = {key: value * 0.9 for key, value in result.items()}
        result["orientation"] = 0.1
    return result
