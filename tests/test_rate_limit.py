from types import SimpleNamespace

from app.core.rate_limit import SlidingWindowRateLimiter, client_key


def test_sliding_window_rejects_requests_over_limit() -> None:
    limiter = SlidingWindowRateLimiter()
    assert limiter.check("login:127.0.0.1", 2) == (True, 0)
    assert limiter.check("login:127.0.0.1", 2) == (True, 0)
    allowed, retry_after = limiter.check("login:127.0.0.1", 2)
    assert not allowed
    assert retry_after > 0


def test_authenticated_rate_limit_key_does_not_contain_token() -> None:
    token = "Bearer secret-token-value"
    request = SimpleNamespace(
        headers={"Authorization": token},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    rule = SimpleNamespace(name="ai")
    key = client_key(request, rule)
    assert "secret-token-value" not in key
    assert key.startswith("ai:")
