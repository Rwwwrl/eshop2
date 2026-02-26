from unittest.mock import AsyncMock, patch

import pytest
from faststream import ContextRepo
from faststream.rabbit import RabbitBroker
from libs.context_vars import request_id_var
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER, REQUEST_ID_HEADER
from libs.faststream_ext.middlewares import RequestIdMiddleware
from libs.faststream_ext.utils import publish
from libs.utils import get_class_full_path
from messaging_contracts.events import HelloWorldEvent


class _StubMessage:
    def __init__(self, headers: dict[str, str]) -> None:
        self.headers = headers


@pytest.fixture(scope="session")
def context() -> ContextRepo:
    return ContextRepo()


@pytest.mark.asyncio(loop_scope="session")
async def test_consume_scope_sets_request_id_from_header(context: ContextRepo) -> None:
    middleware = RequestIdMiddleware(None, context=context)
    msg = _StubMessage(headers={REQUEST_ID_HEADER: "abc-123"})
    call_next = AsyncMock(return_value="ok")

    result = await middleware.consume_scope(call_next=call_next, msg=msg)

    assert result == "ok"
    assert request_id_var.get() == "abc-123"
    call_next.assert_awaited_once_with(msg)
    request_id_var.set(None)


@pytest.mark.asyncio(loop_scope="session")
async def test_consume_scope_skips_when_no_header(context: ContextRepo) -> None:
    middleware = RequestIdMiddleware(None, context=context)
    msg = _StubMessage(headers={})
    call_next = AsyncMock(return_value="ok")
    token = request_id_var.set("existing-id")

    try:
        result = await middleware.consume_scope(call_next=call_next, msg=msg)
        assert result == "ok"
        assert request_id_var.get() == "existing-id"
    finally:
        request_id_var.reset(token)


@pytest.mark.asyncio(loop_scope="session")
async def test_publish_includes_request_id_header_when_set() -> None:
    broker = RabbitBroker()
    token = request_id_var.set("req-456")

    try:
        with patch.object(broker, "publish", new_callable=AsyncMock) as mock_publish:
            await publish(broker=broker, message=HelloWorldEvent(message="hello"))

        mock_publish.assert_awaited_once()
        headers = mock_publish.call_args.kwargs["headers"]
        assert headers[REQUEST_ID_HEADER] == "req-456"
        assert headers[MESSAGE_CLASS_HEADER] == get_class_full_path(cls=HelloWorldEvent)
    finally:
        request_id_var.reset(token)


@pytest.mark.asyncio(loop_scope="session")
async def test_publish_omits_request_id_header_when_not_set() -> None:
    broker = RabbitBroker()

    with patch.object(broker, "publish", new_callable=AsyncMock) as mock_publish:
        await publish(broker=broker, message=HelloWorldEvent(message="hello"))

    mock_publish.assert_awaited_once()
    headers = mock_publish.call_args.kwargs["headers"]
    assert REQUEST_ID_HEADER not in headers
    assert MESSAGE_CLASS_HEADER in headers
