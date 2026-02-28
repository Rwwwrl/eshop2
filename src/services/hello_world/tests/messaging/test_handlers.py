from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from faststream.rabbit import TestRabbitBroker
from hello_world.messaging.handlers import (
    handle_hello_world_async_command,
    handle_hello_world_event,
    handle_open_health_result_received,
)
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER
from libs.faststream_ext.exceptions import DuplicateMessageError
from libs.utils import get_class_full_path
from messaging_contracts.events import HelloWorldEvent, OpenHealthResultReceivedEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand
from rabbitmq_topology.resources import HELLO_WORLD_QUEUE
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_event_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    event = HelloWorldEvent(logical_id=uuid4(), message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    with patch("hello_world.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)

        handle_hello_world_event.mock.assert_called_once()
        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_duplicate_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    logical_id = uuid4()
    event = HelloWorldEvent(logical_id=logical_id, message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    with patch("hello_world.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)

        with pytest.raises(DuplicateMessageError):
            await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)

        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_async_command_when_command_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    command = HelloWorldAsyncCommand(logical_id=uuid4(), greeting="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldAsyncCommand)}

    with patch("hello_world.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=command, queue=HELLO_WORLD_QUEUE.name, headers=headers)

        handle_hello_world_async_command.mock.assert_called_once()
        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_open_health_result_received_when_event_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    event = OpenHealthResultReceivedEvent(logical_id=uuid4(), result_id=42)
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=OpenHealthResultReceivedEvent)}

    with (
        patch("hello_world.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business,
        patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish,
        pytest.raises(RuntimeError, match="Simulated failure for retry test"),
    ):
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)

    handle_open_health_result_received.mock.assert_called_once()
    mock_business.assert_called_once()
    mock_publish.assert_called_once()
