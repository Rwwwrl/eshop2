from uuid import uuid4

from fastapi import APIRouter, Request, status
from grpc_protos.v1.hello_world import hello_world_pb2, hello_world_pb2_grpc
from libs.faststream_ext import publish
from libs.utils import generate_deterministic_uuid
from messaging_contracts.v1.events import HelloWorldEvent, OpenHealthResultReceivedEvent
from messaging_contracts.v1.hello_world.async_commands import HelloWorldAsyncCommand
from starlette.responses import Response

from api_gateway.http.v1.schemas.request_schemas import OpenHealthResultWebhookPayload
from api_gateway.messaging.main import broker as faststream_broker

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "API Gateway"}


@router.get("/debug/error")
async def debug_error() -> None:
    raise RuntimeError("Test unhandled exception")


@router.get("/hello-world/host")
async def get_hello_world_host(request: Request) -> dict:
    stub = hello_world_pb2_grpc.HelloWorldServiceStub(channel=request.app.state.hello_world_grpc_channel)
    response = await stub.GetHost(request=hello_world_pb2.GetHostRequest())
    return {"host": response.host}


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
