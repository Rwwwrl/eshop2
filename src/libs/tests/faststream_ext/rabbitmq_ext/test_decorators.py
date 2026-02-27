from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faststream import ContextRepo
from faststream.exceptions import AckMessage, NackMessage, RejectMessage
from faststream.rabbit import RabbitQueue
from libs.faststream_ext.consts import RETRY_ATTEMPT_HEADER
from libs.faststream_ext.rabbitmq_ext.decorators import retry


class _CustomError(Exception):
    pass


class _AnotherError(Exception):
    pass


def _make_context(queue_name: str = "test-queue", headers: dict[str, str] | None = None) -> MagicMock:
    context = MagicMock(spec=ContextRepo)
    message = MagicMock()
    message.body = b'{"key": "value"}'
    message.headers = headers or {"x-message-class": "some.Class"}
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

    @retry(max_attempts=3, countdown=5)
    async def handler(context: ContextRepo) -> str:
        return "ok"

    result = await handler(context=context)

    assert result == "ok"


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_handler_succeeds_does_not_publish() -> None:
    context = _make_context()

    @retry(max_attempts=3, countdown=5)
    async def handler(context: ContextRepo) -> str:
        return "ok"

    with patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish:
        await handler(context=context)

    mock_publish.assert_not_called()


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_publishes_with_attempt_header_and_countdown() -> None:
    context = _make_context()

    @retry(max_attempts=3, countdown=5)
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
    assert call_kwargs["extra_headers"] == {RETRY_ATTEMPT_HEADER: "1"}
    assert call_kwargs["expiration"] == 5


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_increments_existing_attempt_header() -> None:
    context = _make_context(headers={"x-message-class": "some.Class", RETRY_ATTEMPT_HEADER: "2"})

    @retry(max_attempts=3, countdown=5)
    async def handler(context: ContextRepo) -> None:
        raise ValueError("boom")

    with patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish:
        with pytest.raises(ValueError, match="boom"):
            await handler(context=context)

    call_kwargs = mock_publish.call_args.kwargs
    assert call_kwargs["extra_headers"] == {RETRY_ATTEMPT_HEADER: "3"}


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_max_attempts_exceeded_does_not_publish() -> None:
    context = _make_context(headers={"x-message-class": "some.Class", RETRY_ATTEMPT_HEADER: "3"})

    @retry(max_attempts=3, countdown=5)
    async def handler(context: ContextRepo) -> None:
        raise ValueError("boom")

    with patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish:
        with pytest.raises(ValueError, match="boom"):
            await handler(context=context)

    mock_publish.assert_not_called()


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_max_attempts_exceeded_with_dlq_raises_nack() -> None:
    context = _make_context(headers={"x-message-class": "some.Class", RETRY_ATTEMPT_HEADER: "3"})

    @retry(max_attempts=3, countdown=5, dlq=True)
    async def handler(context: ContextRepo) -> None:
        raise ValueError("boom")

    with patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish:
        with pytest.raises(NackMessage) as exc_info:
            await handler(context=context)

    assert exc_info.value.extra_options == {"requeue": False}
    mock_publish.assert_not_called()


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_when_specific_exception_does_not_match_propagates() -> None:
    context = _make_context()

    @retry(max_attempts=3, countdown=5, exceptions=(_CustomError,))
    async def handler(context: ContextRepo) -> None:
        raise _AnotherError("another boom")

    with pytest.raises(_AnotherError, match="another boom"):
        await handler(context=context)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_preserves_wrapped_function_name() -> None:
    @retry(max_attempts=3, countdown=5)
    async def my_handler(context: ContextRepo) -> None:
        pass

    assert my_handler.__name__ == "my_handler"
    assert my_handler.__wrapped__.__name__ == "my_handler"


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_does_not_intercept_ack_message() -> None:
    context = _make_context()

    @retry(max_attempts=3, countdown=5)
    async def handler(context: ContextRepo) -> None:
        raise AckMessage()

    with pytest.raises(AckMessage):
        await handler(context=context)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_does_not_intercept_nack_message() -> None:
    context = _make_context()

    @retry(max_attempts=3, countdown=5)
    async def handler(context: ContextRepo) -> None:
        raise NackMessage()

    with pytest.raises(NackMessage):
        await handler(context=context)


@pytest.mark.asyncio(loop_scope="session")
async def test_retry_does_not_intercept_reject_message() -> None:
    context = _make_context()

    @retry(max_attempts=3, countdown=5)
    async def handler(context: ContextRepo) -> None:
        raise RejectMessage()

    with pytest.raises(RejectMessage):
        await handler(context=context)
