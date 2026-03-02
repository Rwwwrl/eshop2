from uuid import uuid4

import httpx
from fastapi import APIRouter, status
from libs.consts import REQUEST_ID_HEADER
from libs.context_vars import request_id_var
from libs.faststream_ext import publish
from libs.utils import generate_deterministic_uuid
from messaging_contracts.v1.events import HelloWorldEvent, OpenHealthResultReceivedEvent
from messaging_contracts.v1.hello_world.async_commands import HelloWorldAsyncCommand
from starlette.responses import Response

from api_gateway.http.v1.schemas.request_schemas import OpenHealthResultWebhookPayload
from api_gateway.messaging.main import broker as faststream_broker

router = APIRouter()

_HELLO_WORLD_SERVICE_URL = "http://hello-world"


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "API Gateway"}


@router.get("/debug/error")
async def debug_error() -> None:
    raise RuntimeError("Test unhandled exception")


@router.get("/hello-world/host")
async def get_hello_world_host() -> dict:
    headers = {REQUEST_ID_HEADER: request_id_var.get()}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{_HELLO_WORLD_SERVICE_URL}/v1/host", headers=headers)
        return response.json()


@router.post("/debug/publish-hello-world", status_code=status.HTTP_202_ACCEPTED)
async def publish_hello_world() -> dict[str, str]:
    event = HelloWorldEvent(logical_id=uuid4(), message="Hello from API Gateway!")
    await publish(broker=faststream_broker, message=event)
    return {"status": "published"}


@router.post("/debug/publish-hello-world-async-command", status_code=status.HTTP_202_ACCEPTED)
async def publish_hello_world_async_command() -> dict[str, str]:
    command = HelloWorldAsyncCommand(logical_id=uuid4(), greeting="Greetings from API Gateway!")
    await publish(broker=faststream_broker, message=command)
    return {"status": "published"}


@router.post("/open-health/result-webhook", status_code=status.HTTP_202_ACCEPTED)
async def open_health_result_webhook(body: OpenHealthResultWebhookPayload) -> Response:
    event = OpenHealthResultReceivedEvent(
        logical_id=generate_deterministic_uuid(key=(body.result_id,)),
        result_id=body.result_id,
    )
    await publish(broker=faststream_broker, message=event)

    return Response(status_code=status.HTTP_202_ACCEPTED)
