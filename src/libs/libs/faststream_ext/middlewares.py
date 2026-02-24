import asyncio
from collections.abc import Callable
from logging import getLogger
from typing import Any

from faststream import BaseMiddleware, ContextRepo
from faststream.message import StreamMessage

from libs.context_vars import request_id_var
from libs.faststream_ext.consts import REQUEST_ID_HEADER

_logger = getLogger(__name__)

_DEFAULT_TIMEOUT_SECONDS = 60.0


class RequestIdMiddleware(BaseMiddleware):
    async def consume_scope(self, call_next: Callable[..., Any], msg: StreamMessage[Any]) -> Any:
        request_id = msg.headers.get(REQUEST_ID_HEADER)

        if request_id is not None:
            request_id_var.set(request_id)

        return await call_next(msg)


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
