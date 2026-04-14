import functools
import time
from typing import Callable, Type

from utils.logger import get_logger

log = get_logger("retry")


def retry(
    max_attempts: int = 3,
    backoff_base: float = 2,
    exceptions: tuple[Type[BaseException], ...] = (Exception,),
):
    """Retry a function with exponential backoff.

    Sleep pattern: backoff_base^0, backoff_base^1, ..., backoff_base^(n-2).
    With backoff_base=2 and max_attempts=4: 1s, 2s, 4s.
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts - 1:
                        log.error(f"{func.__name__} {max_attempts} denemeden sonra başarısız: {e}")
                        raise
                    wait = backoff_base ** attempt if backoff_base > 0 else 0
                    log.warning(f"{func.__name__} denemesi {attempt + 1} başarısız ({e}), {wait}s bekleniyor")
                    time.sleep(wait)
            raise last_exc  # unreachable
        return wrapper
    return decorator
