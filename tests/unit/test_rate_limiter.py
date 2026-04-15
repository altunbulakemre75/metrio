import time
from utils.rate_limiter import rate_limit, jitter_delay


def test_rate_limit_allows_first_call_immediately():
    @rate_limit(calls_per_second=10)
    def work():
        return "ok"

    start = time.monotonic()
    work()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


def test_rate_limit_delays_second_call():
    @rate_limit(calls_per_second=10)  # min gap 0.1s
    def work():
        return "ok"

    work()
    start = time.monotonic()
    work()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.09


def test_rate_limit_independent_per_function():
    @rate_limit(calls_per_second=10)
    def work_a():
        return "a"

    @rate_limit(calls_per_second=10)
    def work_b():
        return "b"

    work_a()
    start = time.monotonic()
    work_b()
    elapsed = time.monotonic() - start
    assert elapsed < 0.05


def test_jitter_delay_waits_within_range():
    calls = []

    @jitter_delay(min_seconds=0.01, max_seconds=0.03)
    def fn():
        calls.append(time.monotonic())

    t0 = time.monotonic()
    fn()
    fn()
    elapsed = calls[1] - calls[0]
    # 2 çağrı arası ~10-30ms bekleme
    assert 0.01 <= elapsed <= 0.1


def test_jitter_delay_returns_function_value():
    @jitter_delay(0.001, 0.002)
    def fn(x):
        return x * 2
    assert fn(5) == 10
