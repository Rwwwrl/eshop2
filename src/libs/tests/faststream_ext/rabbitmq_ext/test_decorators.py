from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faststream import ContextRepo
from faststream.exceptions import AckMessage, NackMessage, RejectMessage
from faststream.rabbit import RabbitQueue
from libs.faststream_ext.rabbitmq_ext.decorators import retry


class _CustomError(Exception):
    pass


class _AnotherError(Exception):
    pass


def _make_context(queue_name: str = "test-queue") -> MagicMock:
    context = MagicMock(spec=ContextRepo)
    message = MagicMock()
    message.body = b'{"key": "value"}'
    message.headers = {"x-message-class": "some.Class"}
    broker = AsyncMock()
    handler = MagicMock()
    handler.queue = RabbitQueue(name=queue_name)

    def _resolve(key: str) -> object:
        return {"message": message, "broker": broker, "handler_": handler}[key]

    context.resolve.side_effect = _resolve
    return context


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_handler_succeeds() -> None:
    context = _make_context()

    @retry()
    async def handler(context: ContextRepo) -> str:
        return "ok"

    result = await handler(context=context)

    assert result == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_handler_succeeds_does_not_publish() -> None:
    context = _make_context()

    @retry()
    async def handler(context: ContextRepo) -> str:
        return "ok"

    with patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish:
        await handler(context=context)

    mock_publish.assert_not_called()


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_handler_raises_exception_publishes_to_delayed_retry() -> None:
    context = _make_context()

    @retry()
    async def handler(context: ContextRepo) -> None:
        raise ValueError("boom")

    with patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish:
        with pytest.raises(ValueError, match="boom"):
            await handler(context=context)

    mock_publish.assert_called_once()
    call_kwargs = mock_publish.call_args.kwargs
    assert call_kwargs["broker"] is context.resolve("broker")
    assert call_kwargs["message"] is context.resolve("message")
    assert call_kwargs["original_queue"].name == "test-queue"


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_specific_exception_does_not_match_propagates() -> None:
    context = _make_context()

    @retry(exceptions=(_CustomError,))
    async def handler(context: ContextRepo) -> None:
        raise _AnotherError("another boom")

    with pytest.raises(_AnotherError, match="another boom"):
        await handler(context=context)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_preserves_wrapped_function_name() -> None:
    @retry()
    async def my_handler(context: ContextRepo) -> None:
        pass

    assert my_handler.__name__ == "my_handler"
    assert my_handler.__wrapped__.__name__ == "my_handler"


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_does_not_intercept_ack_message() -> None:
    context = _make_context()

    @retry()
    async def handler(context: ContextRepo) -> None:
        raise AckMessage()

    with pytest.raises(AckMessage):
        await handler(context=context)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_does_not_intercept_nack_message() -> None:
    context = _make_context()

    @retry()
    async def handler(context: ContextRepo) -> None:
        raise NackMessage()

    with pytest.raises(NackMessage):
        await handler(context=context)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_does_not_intercept_reject_message() -> None:
    context = _make_context()

    @retry()
    async def handler(context: ContextRepo) -> None:
        raise RejectMessage()

    with pytest.raises(RejectMessage):
        await handler(context=context)
