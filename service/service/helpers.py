import random
import time
from collections.abc import Callable
from typing import Any

from .logger import log


def try_ignore(fb: Any = None, fbcall: Callable | None = None) -> Callable:  # noqa

    def decorator(func: Callable) -> Callable:
        def wrapper(*args: tuple, **kwargs: dict) -> Any:  # noqa
            try:
                return func(*args, **kwargs)
            except Exception as e:
                log.error("try-ignore %s: %s", func.__name__, e)
                if fbcall:
                    try:
                        return fbcall(*args, **kwargs)
                    except Exception as e:
                        log.error("try-ignore fbcall %s: %s", fbcall.__name__, e)
                return fb

        return wrapper

    return decorator


def sleeq(secs: float) -> None:
    time.sleep(random.uniform(secs * 0.75, secs * 1.5))


def rndstr(length: int = 64) -> str:
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choices(letters, k=length))
