from collections.abc import Callable
from functools import wraps
from typing import Any

from faststream.exceptions import NackMessage


def dlq(exceptions: tuple[type[Exception], ...] = (Exception,)) -> Callable[..., Any]:
    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def _wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except exceptions:
                raise NackMessage(requeue=False)

        return _wrapper

    return _decorator
