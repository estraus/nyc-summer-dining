from __future__ import annotations

from app.rate_limit import SlidingWindowLimiter


def test_allows_up_to_limit() -> None:
    now = [0.0]
    limiter = SlidingWindowLimiter(max_attempts=3, window_seconds=60, clock=lambda: now[0])
    for _ in range(3):
        assert limiter.check("1.2.3.4") is None


def test_rejects_when_limit_exceeded() -> None:
    now = [100.0]
    limiter = SlidingWindowLimiter(max_attempts=2, window_seconds=60, clock=lambda: now[0])
    assert limiter.check("ip") is None
    assert limiter.check("ip") is None
    retry_after = limiter.check("ip")
    assert retry_after is not None
    assert 0 < retry_after <= 60


def test_window_resets_after_expiry() -> None:
    now = [0.0]
    limiter = SlidingWindowLimiter(max_attempts=1, window_seconds=10, clock=lambda: now[0])
    assert limiter.check("ip") is None
    assert limiter.check("ip") is not None
    now[0] = 11.0
    assert limiter.check("ip") is None


def test_separate_keys_have_independent_counters() -> None:
    now = [0.0]
    limiter = SlidingWindowLimiter(max_attempts=1, window_seconds=60, clock=lambda: now[0])
    assert limiter.check("a") is None
    assert limiter.check("b") is None
    assert limiter.check("a") is not None
