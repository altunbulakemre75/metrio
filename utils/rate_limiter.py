import functools
import random
import time
from typing import Callable


def rate_limit(calls_per_second: float):
    """Ensure at least 1/calls_per_second seconds between calls to this function.

    Each decorated function keeps its own last-call timestamp.
    """
    if calls_per_second <= 0:
        raise ValueError("calls_per_second must be positive")

    min_interval = 1.0 / calls_per_second

    def decorator(func: Callable):
        last_call = [0.0]

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            now = time.monotonic()
            wait = min_interval - (now - last_call[0])
            if wait > 0:
                time.sleep(wait)
            last_call[0] = time.monotonic()
            return func(*args, **kwargs)

        return wrapper
    return decorator


def jitter_delay(min_seconds: float, max_seconds: float):
    """Her çağrıdan önce uniform(min, max) saniye bekler."""
    if min_seconds < 0 or max_seconds < min_seconds:
        raise ValueError("geçersiz jitter aralığı")

    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            time.sleep(random.uniform(min_seconds, max_seconds))
            return func(*args, **kwargs)
        return wrapper
    return decorator
