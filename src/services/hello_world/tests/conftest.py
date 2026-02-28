from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from faststream.rabbit import TestRabbitBroker
from hello_world.http.routes import router
from hello_world.messaging.main import broker as faststream_broker
from hello_world.settings import Settings
from hello_world.settings import settings as hello_world_settings
from httpx import ASGITransport, AsyncClient
from libs.fastapi_ext.middlewares import UnhandledExceptionMiddleware
from libs.faststream_ext.models import ProcessedMessage
from libs.sqlmodel_ext import BaseSqlModel


@pytest.fixture(scope="session")
def settings() -> Settings:
    return hello_world_settings


@pytest.fixture(scope="session")
def autocleared_sqlmodel_tables() -> list[type[BaseSqlModel]]:
    return [ProcessedMessage]


@pytest.fixture(scope="session")
def fastapi_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(UnhandledExceptionMiddleware)
    app.include_router(router=router)
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
