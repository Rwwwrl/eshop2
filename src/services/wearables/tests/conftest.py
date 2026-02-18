from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from libs.sqlmodel_ext import BaseSqlModel, Session
from sqlalchemy.ext.asyncio import AsyncEngine
from taskiq import AsyncBroker, InMemoryBroker
from taskiq.brokers.shared_broker import async_shared_broker
from wearables.http.routes import router
from wearables.models import WearableEvent
from wearables.settings import settings as wearables_settings


@pytest.fixture(scope="session")
def settings() -> wearables_settings.__class__:
    return wearables_settings


@pytest.fixture(scope="session")
def autocleared_sqlmodel_tables() -> list[type[BaseSqlModel]]:
    return [WearableEvent]


@pytest_asyncio.fixture(scope="session")
async def taskiq_broker(sqlmodel_engine: AsyncEngine) -> AsyncGenerator[AsyncBroker]:
    Session.configure(bind=sqlmodel_engine)
    test_broker = InMemoryBroker()
    async_shared_broker.default_broker(test_broker)
    await test_broker.startup()
    yield test_broker
    await test_broker.shutdown()


@pytest_asyncio.fixture(scope="session")
async def fastapi_app(sqlmodel_engine: AsyncEngine, taskiq_broker: AsyncBroker) -> AsyncGenerator[FastAPI]:
    app = FastAPI()
    app.state.sqlmodel_engine = sqlmodel_engine
    app.include_router(router=router)
    yield app
