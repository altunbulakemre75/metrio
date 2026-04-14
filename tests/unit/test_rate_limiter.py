import time
from utils.rate_limiter import rate_limit


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
