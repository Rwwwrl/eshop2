from unittest.mock import AsyncMock

import pytest
from libs.context_vars import request_id_var
from libs.grpc_ext.interceptors.request_id import RequestIdClientInterceptor, RequestIdServerInterceptor


class _StubClientCallDetails:
    def __init__(self, metadata: list[tuple[str, str]] | None = None) -> None:
        self.method = "/test.Service/Method"
        self.timeout = None
        self.metadata = metadata
        self.credentials = None
        self.wait_for_ready = None


class _StubHandlerCallDetails:
    def __init__(self, metadata: list[tuple[str, str]] | None = None) -> None:
        self.method = "/test.Service/Method"
        self.invocation_metadata = metadata


# --- Client interceptor ---


@pytest.mark.asyncio(loop_scope="session")
async def test_client_interceptor_injects_request_id_into_metadata() -> None:
    interceptor = RequestIdClientInterceptor()
    continuation = AsyncMock(return_value="response")
    call_details = _StubClientCallDetails()
    token = request_id_var.set("abc-123")

    try:
        result = await interceptor.intercept_unary_unary(
            continuation=continuation,
            client_call_details=call_details,
            request="req",
        )
    finally:
        request_id_var.reset(token)

    assert result == "response"
    sent_details = continuation.call_args[0][0]
    assert ("x-request-id", "abc-123") in sent_details.metadata


@pytest.mark.asyncio(loop_scope="session")
async def test_client_interceptor_preserves_existing_metadata() -> None:
    interceptor = RequestIdClientInterceptor()
    continuation = AsyncMock(return_value="response")
    call_details = _StubClientCallDetails(metadata=[("authorization", "Bearer token")])
    token = request_id_var.set("abc-123")

    try:
        await interceptor.intercept_unary_unary(
            continuation=continuation,
            client_call_details=call_details,
            request="req",
        )
    finally:
        request_id_var.reset(token)

    sent_details = continuation.call_args[0][0]
    assert ("authorization", "Bearer token") in sent_details.metadata
    assert ("x-request-id", "abc-123") in sent_details.metadata


@pytest.mark.asyncio(loop_scope="session")
async def test_client_interceptor_skips_when_no_request_id() -> None:
    interceptor = RequestIdClientInterceptor()
    continuation = AsyncMock(return_value="response")
    call_details = _StubClientCallDetails()

    result = await interceptor.intercept_unary_unary(
        continuation=continuation,
        client_call_details=call_details,
        request="req",
    )

    assert result == "response"
    sent_details = continuation.call_args[0][0]
    assert sent_details is call_details


# --- Server interceptor ---


@pytest.mark.asyncio(loop_scope="session")
async def test_server_interceptor_sets_request_id_from_metadata() -> None:
    interceptor = RequestIdServerInterceptor()
    handler = AsyncMock()
    continuation = AsyncMock(return_value=handler)
    call_details = _StubHandlerCallDetails(metadata=[("x-request-id", "abc-123")])

    try:
        result = await interceptor.intercept_service(
            continuation=continuation,
            handler_call_details=call_details,
        )

        assert result is handler
        assert request_id_var.get() == "abc-123"
    finally:
        request_id_var.set(None)


@pytest.mark.asyncio(loop_scope="session")
async def test_server_interceptor_skips_when_no_metadata() -> None:
    interceptor = RequestIdServerInterceptor()
    handler = AsyncMock()
    continuation = AsyncMock(return_value=handler)
    call_details = _StubHandlerCallDetails(metadata=[])
    token = request_id_var.set("existing-id")

    try:
        result = await interceptor.intercept_service(
            continuation=continuation,
            handler_call_details=call_details,
        )
        assert result is handler
        assert request_id_var.get() == "existing-id"
    finally:
        request_id_var.reset(token)


@pytest.mark.asyncio(loop_scope="session")
async def test_server_interceptor_skips_when_no_request_id_key() -> None:
    interceptor = RequestIdServerInterceptor()
    handler = AsyncMock()
    continuation = AsyncMock(return_value=handler)
    call_details = _StubHandlerCallDetails(metadata=[("authorization", "Bearer token")])
    token = request_id_var.set("existing-id")

    try:
        await interceptor.intercept_service(
            continuation=continuation,
            handler_call_details=call_details,
        )
        assert request_id_var.get() == "existing-id"
    finally:
        request_id_var.reset(token)
