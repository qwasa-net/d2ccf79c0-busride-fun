import random
import time
from collections.abc import Callable
from typing import Any

from .logger import log


def try_except(fallback: Any = None) -> Callable:  # noqa

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: tuple, **kwargs: dict) -> Any:  # noqa
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # log.exception("Exception in %s: %s", func.__name__, e)
                log.error("%s: %s", func.__name__, e)
                return fallback

        return wrapper

    return decorator


def sleeq(secs: float) -> None:
    time.sleep(random.uniform(secs * 0.75, secs * 1.5))
