from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from libs.sqlmodel_ext import BaseSqlModel
from taskiq import AsyncBroker
from wearables.messaging.main import broker
from wearables.models import WearableEvent
from wearables.settings import settings as wearables_settings


@pytest.fixture(scope="session")
def settings() -> wearables_settings.__class__:
    return wearables_settings


@pytest.fixture(scope="session")
def autocleared_sqlmodel_tables() -> list[type[BaseSqlModel]]:
    return [WearableEvent]


@pytest_asyncio.fixture(scope="session")
async def taskiq_broker() -> AsyncGenerator[AsyncBroker]:
    await broker.startup()
    yield broker
    await broker.shutdown()
