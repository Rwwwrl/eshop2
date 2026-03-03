from collections.abc import Callable
from typing import Any

import grpc

from libs.context_vars import request_id_var

_GRPC_REQUEST_ID_KEY = "x-request-id"


class RequestIdClientInterceptor(grpc.aio.UnaryUnaryClientInterceptor):
    async def intercept_unary_unary(
        self,
        continuation: Callable[..., Any],
        client_call_details: grpc.aio.ClientCallDetails,
        request: Any,
    ) -> Any:
        request_id = request_id_var.get()

        if request_id is not None:
            metadata = list(client_call_details.metadata) if client_call_details.metadata else []
            metadata.append((_GRPC_REQUEST_ID_KEY, request_id))
            client_call_details = grpc.aio.ClientCallDetails(
                method=client_call_details.method,
                timeout=client_call_details.timeout,
                metadata=metadata,
                credentials=client_call_details.credentials,
                wait_for_ready=client_call_details.wait_for_ready,
            )

        return await continuation(client_call_details, request)


class RequestIdServerInterceptor(grpc.aio.ServerInterceptor):
    async def intercept_service(
        self,
        continuation: Callable[..., Any],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Any:
        metadata = handler_call_details.invocation_metadata
        if metadata is not None:
            for key, value in metadata:
                if key == _GRPC_REQUEST_ID_KEY:
                    request_id_var.set(value)
                    break

        return await continuation(handler_call_details)
