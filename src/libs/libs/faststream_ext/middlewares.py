import asyncio
from collections.abc import Callable
from logging import getLogger
from typing import Any

from faststream import BaseMiddleware, ContextRepo

_logger = getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 60.0


class TimeLimitMiddleware(BaseMiddleware):
    def __init__(self, msg: Any, /, *, context: ContextRepo, timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS) -> None:
        super().__init__(msg, context=context)
        self._timeout_seconds = timeout_seconds

    async def consume_scope(self, call_next: Callable[..., Any], msg: Any) -> Any:
        try:
            return await asyncio.wait_for(call_next(msg), timeout=self._timeout_seconds)
        except asyncio.TimeoutError:
            _logger.error("Message processing timed out after %.1fs", self._timeout_seconds)
            raise
