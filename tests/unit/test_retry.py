import pytest
from utils.retry import retry


def test_retry_succeeds_on_first_try():
    calls = []

    @retry(max_attempts=3, backoff_base=0)
    def work():
        calls.append(1)
        return "ok"

    assert work() == "ok"
    assert len(calls) == 1


def test_retry_succeeds_on_second_attempt():
    calls = []

    @retry(max_attempts=3, backoff_base=0)
    def work():
        calls.append(1)
        if len(calls) < 2:
            raise ConnectionError("boom")
        return "ok"

    assert work() == "ok"
    assert len(calls) == 2


def test_retry_exhausts_attempts_and_reraises():
    calls = []

    @retry(max_attempts=3, backoff_base=0)
    def work():
        calls.append(1)
        raise ConnectionError("always fails")

    with pytest.raises(ConnectionError, match="always fails"):
        work()
    assert len(calls) == 3


def test_retry_does_not_catch_unspecified_exceptions():
    calls = []

    @retry(max_attempts=3, backoff_base=0, exceptions=(ConnectionError,))
    def work():
        calls.append(1)
        raise ValueError("not retriable")

    with pytest.raises(ValueError):
        work()
    assert len(calls) == 1


def test_retry_exponential_backoff(monkeypatch):
    sleeps = []
    monkeypatch.setattr("utils.retry.time.sleep", lambda s: sleeps.append(s))

    @retry(max_attempts=4, backoff_base=2)
    def work():
        raise ConnectionError("boom")

    with pytest.raises(ConnectionError):
        work()

    assert sleeps == [1, 2, 4]
