from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
from threading import Lock
from time import monotonic

from fastapi import Request

from app.core.config import Settings


@dataclass(frozen=True)
class RateLimitRule:
    name: str
    limit: int


class SlidingWindowRateLimiter:
    """Small-process rate limiter for the single-worker home deployment."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> tuple[bool, int]:
        now = monotonic()
        cutoff = now - window_seconds
        with self._lock:
            events = self._events[key]
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(window_seconds - (now - events[0])) + 1)
                return False, retry_after
            events.append(now)
            return True, 0


def rule_for_request(request: Request, settings: Settings) -> RateLimitRule | None:
    if not settings.rate_limit_enabled or request.method != "POST":
        return None
    path = request.url.path
    if path == "/api/v1/auth/register":
        return RateLimitRule("register", settings.rate_limit_register_per_minute)
    if path == "/api/v1/auth/login":
        return RateLimitRule("login", settings.rate_limit_login_per_minute)
    if path.endswith("/messages/stream") or (
        path.startswith("/api/v1/recommendations/") and path.endswith("/refine")
    ):
        return RateLimitRule("ai", settings.rate_limit_ai_per_minute)
    if path == "/api/v1/admin/tags/generate":
        return RateLimitRule("batch-tag", settings.rate_limit_batch_tag_per_minute)
    return None


def client_key(request: Request, rule: RateLimitRule) -> str:
    authorization = request.headers.get("Authorization", "")
    if rule.name in {"ai", "batch-tag"} and authorization:
        identity = sha256(authorization.encode("utf-8")).hexdigest()
    else:
        identity = request.client.host if request.client else "unknown"
    return f"{rule.name}:{identity}"
