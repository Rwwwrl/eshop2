from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from faststream.rabbit import TestRabbitBroker
from hello_world.messaging.v1.handlers import (
    handle_hello_world_async_command,
    handle_hello_world_event,
    handle_open_health_result_received,
)
from libs.faststream_ext.exceptions import DuplicateMessageError
from messaging_contracts.v1.events import HelloWorldEvent, OpenHealthResultReceivedEvent
from messaging_contracts.v1.hello_world.async_commands import HelloWorldAsyncCommand
from rabbitmq_topology.resources import HELLO_WORLD_QUEUE
from sqlalchemy.ext.asyncio import AsyncEngine


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_event_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    event = HelloWorldEvent(logical_id=uuid4(), message="Hello from test!")

    with patch("hello_world.messaging.v1.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)

        handle_hello_world_event.mock.assert_called_once()
        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_duplicate_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    logical_id = uuid4()
    event = HelloWorldEvent(logical_id=logical_id, message="Hello from test!")

    with patch("hello_world.messaging.v1.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)

        with pytest.raises(DuplicateMessageError):
            await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)

        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_same_logical_id_but_different_message_code(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    logical_id = uuid4()
    event = HelloWorldEvent(logical_id=logical_id, message="Hello from test!")
    command = HelloWorldAsyncCommand(logical_id=logical_id, greeting="Hello from test!")

    with patch("hello_world.messaging.v1.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)
        await test_broker.publish(message=command, queue=HELLO_WORLD_QUEUE.name)

        assert mock_business.call_count == 2


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_async_command_when_command_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    command = HelloWorldAsyncCommand(logical_id=uuid4(), greeting="Hello from test!")

    with patch("hello_world.messaging.v1.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=command, queue=HELLO_WORLD_QUEUE.name)

        handle_hello_world_async_command.mock.assert_called_once()
        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_open_health_result_received_when_event_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    event = OpenHealthResultReceivedEvent(logical_id=uuid4(), result_id=42)

    with (
        patch("hello_world.messaging.v1.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business,
        patch("libs.faststream_ext.rabbitmq_ext.decorators.publish_to_delayed_retry_queue") as mock_publish,
        pytest.raises(RuntimeError, match="Simulated failure for retry test"),
    ):
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)

    handle_open_health_result_received.mock.assert_called_once()
    mock_business.assert_called_once()
    mock_publish.assert_called_once()
