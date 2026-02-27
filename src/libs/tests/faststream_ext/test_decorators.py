import pytest
from faststream.exceptions import NackMessage
from libs.faststream_ext.decorators import dlq


class _CustomError(Exception):
    pass


class _AnotherError(Exception):
    pass


@pytest.mark.asyncio(loop_scope="session")
async def test_dlq_when_handler_succeeds() -> None:
    @dlq()
    async def handler() -> str:
        return "ok"

    result = await handler()
    assert result == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_dlq_when_handler_raises_exception() -> None:
    @dlq()
    async def handler() -> None:
        raise ValueError("boom")

    with pytest.raises(NackMessage):
        await handler()


@pytest.mark.asyncio(loop_scope="session")
async def test_dlq_when_handler_raises_nack_message_with_requeue_false() -> None:
    @dlq()
    async def handler() -> None:
        raise ValueError("boom")

    with pytest.raises(NackMessage) as exc_info:
        await handler()

    assert exc_info.value.extra_options == {"requeue": False}


@pytest.mark.asyncio(loop_scope="session")
async def test_dlq_when_specific_exception_matches() -> None:
    @dlq(exceptions=(_CustomError,))
    async def handler() -> None:
        raise _CustomError("custom boom")

    with pytest.raises(NackMessage):
        await handler()


@pytest.mark.asyncio(loop_scope="session")
async def test_dlq_when_specific_exception_does_not_match() -> None:
    @dlq(exceptions=(_CustomError,))
    async def handler() -> None:
        raise _AnotherError("another boom")

    with pytest.raises(_AnotherError, match="another boom"):
        await handler()


@pytest.mark.asyncio(loop_scope="session")
async def test_dlq_preserves_wrapped_function_name() -> None:
    @dlq()
    async def my_handler() -> None:
        pass

    assert my_handler.__name__ == "my_handler"
    assert my_handler.__wrapped__.__name__ == "my_handler"
