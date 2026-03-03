from collections.abc import AsyncGenerator

import grpc
import pytest_asyncio
from api_gateway.http.v1 import v1_router
from api_gateway.messaging.main import broker as faststream_broker
from fastapi import FastAPI
from faststream.rabbit import TestRabbitBroker
from httpx import ASGITransport, AsyncClient
from libs.fastapi_ext.middlewares import UnhandledExceptionMiddleware


@pytest_asyncio.fixture(scope="session")
async def fastapi_app() -> AsyncGenerator[FastAPI, None]:
    channel = grpc.aio.insecure_channel(target="localhost:50051")
    app = FastAPI()
    app.add_middleware(UnhandledExceptionMiddleware)
    app.include_router(router=v1_router, prefix="/v1")
    app.state.hello_world_grpc_channel = channel
    yield app
    await channel.close()


@pytest_asyncio.fixture(scope="session")
async def async_client(fastapi_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def test_broker() -> AsyncGenerator[TestRabbitBroker, None]:
    async with TestRabbitBroker(faststream_broker) as br:
        yield br
