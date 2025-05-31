import asyncio
import random
from collections.abc import Callable
from typing import Any

from .logger import log


def async_try_ignore(fb: Any = None, fbcall: Callable | None = None) -> Callable:  # noqa
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args: tuple, **kwargs: dict) -> Any:  # noqa
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log.error("async-try-ignore %s: %s", func.__name__, e)
                if fbcall:
                    try:
                        return await fbcall(*args, **kwargs)
                    except Exception as e:
                        log.error("async-try-ignore fbcall %s: %s", fbcall.__name__, e)
                return fb

        return wrapper

    return decorator


async def asleeq(secs: float) -> None:
    await asyncio.sleep(random.uniform(secs * 0.75, secs * 1.5))


def rndstr(length: int = 64) -> str:
    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.choices(letters, k=length))
