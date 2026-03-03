from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from faststream.rabbit import TestRabbitBroker
from hello_world.messaging.main import broker as faststream_broker
from hello_world.settings import Settings
from hello_world.settings import settings as hello_world_settings
from libs.faststream_ext.models import ProcessedMessage
from libs.sqlmodel_ext import BaseSqlModel


@pytest.fixture(scope="session")
def settings() -> Settings:
    return hello_world_settings


@pytest.fixture(scope="session")
def autocleared_sqlmodel_tables() -> list[type[BaseSqlModel]]:
    return [ProcessedMessage]


@pytest_asyncio.fixture(scope="function")
async def test_broker() -> AsyncGenerator[TestRabbitBroker, None]:
    async with TestRabbitBroker(faststream_broker) as br:
        yield br
