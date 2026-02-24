import asyncio
from functools import partial

import pytest
from faststream import ContextRepo
from libs.faststream_ext.middlewares import TimeLimitMiddleware


@pytest.fixture
def context() -> ContextRepo:
    return ContextRepo()


@pytest.mark.asyncio
async def test_completes_within_timeout(context: ContextRepo) -> None:
    middleware = partial(TimeLimitMiddleware, timeout_seconds=1.0)(None, context=context)

    async def _fast_handler(msg: object) -> str:
        return "ok"

    result = await middleware.consume_scope(call_next=_fast_handler, msg=None)

    assert result == "ok"


@pytest.mark.asyncio
async def test_raises_timeout_error_when_exceeded(context: ContextRepo) -> None:
    middleware = partial(TimeLimitMiddleware, timeout_seconds=0.05)(None, context=context)

    async def _slow_handler(msg: object) -> str:
        await asyncio.sleep(1.0)
        return "should not reach"

    with pytest.raises(asyncio.TimeoutError):
        await middleware.consume_scope(call_next=_slow_handler, msg=None)


@pytest.mark.asyncio
async def test_uses_default_timeout(context: ContextRepo) -> None:
    middleware = TimeLimitMiddleware(None, context=context)

    assert middleware._timeout_seconds == 60.0
