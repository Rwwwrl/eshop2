import httpx
from fastapi import APIRouter, status
from libs.consts import REQUEST_ID_HEADER
from libs.context_vars import request_id_var
from libs.faststream_ext import publish
from messaging_contracts.events import HelloWorldEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand

from api_gateway.messaging.main import broker as faststream_broker

router = APIRouter()

_HELLO_WORLD_SERVICE_URL = "http://hello-world"


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "API Gateway"}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/debug/error")
async def debug_error() -> None:
    raise RuntimeError("Test unhandled exception")


@router.get("/hello-world/host")
async def get_hello_world_host() -> dict:
    headers = {REQUEST_ID_HEADER: request_id_var.get()}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{_HELLO_WORLD_SERVICE_URL}/host", headers=headers)
        return response.json()


@router.post("/debug/publish-hello-world", status_code=status.HTTP_202_ACCEPTED)
async def publish_hello_world() -> dict[str, str]:
    event = HelloWorldEvent(message="Hello from API Gateway!")
    await publish(broker=faststream_broker, message=event)
    return {"status": "published"}


@router.post("/debug/publish-hello-world-async-command", status_code=status.HTTP_202_ACCEPTED)
async def publish_hello_world_async_command() -> dict[str, str]:
    command = HelloWorldAsyncCommand(greeting="Greetings from API Gateway!")
    await publish(broker=faststream_broker, message=command)
    return {"status": "published"}
