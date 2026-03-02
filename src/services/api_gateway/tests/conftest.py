from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from api_gateway.http.v1 import v1_router
from api_gateway.messaging.main import broker as faststream_broker
from fastapi import FastAPI
from faststream.rabbit import TestRabbitBroker
from httpx import ASGITransport, AsyncClient
from libs.fastapi_ext.middlewares import UnhandledExceptionMiddleware


@pytest.fixture(scope="session")
def fastapi_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(UnhandledExceptionMiddleware)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readiness_check")
    async def readiness_check() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(router=v1_router, prefix="/v1")
    return app


@pytest_asyncio.fixture(scope="session")
async def async_client(fastapi_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def test_broker() -> AsyncGenerator[TestRabbitBroker]:
    async with TestRabbitBroker(faststream_broker) as br:
        yield br
