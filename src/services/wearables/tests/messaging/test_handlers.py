from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from faststream.rabbit import TestRabbitBroker
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER
from libs.faststream_ext.exceptions import DuplicateMessageError
from libs.utils import get_class_full_path
from messaging_contracts.events import HelloWorldEvent
from rabbitmq_topology.resources import WEARABLES_QUEUE
from sqlalchemy.ext.asyncio import AsyncEngine
from wearables.messaging.handlers import handle_hello_world_event


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_event_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    event = HelloWorldEvent(logical_id=uuid4(), message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    with patch("wearables.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=WEARABLES_QUEUE.name, headers=headers)

        handle_hello_world_event.mock.assert_called_once()
        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_duplicate_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    logical_id = uuid4()
    event = HelloWorldEvent(logical_id=logical_id, message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    with patch("wearables.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=WEARABLES_QUEUE.name, headers=headers)

        with pytest.raises(DuplicateMessageError):
            await test_broker.publish(message=event, queue=WEARABLES_QUEUE.name, headers=headers)

        mock_business.assert_called_once()
