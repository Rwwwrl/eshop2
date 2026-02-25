from unittest.mock import patch

import pytest
from faststream.redis import TestRedisBroker
from hello_world.messaging.handlers import handle_hello_world_async_command, handle_hello_world_event
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER
from libs.faststream_ext.utils import get_message_class_path
from messaging_contracts.consts import HELLO_WORLD_STREAM
from messaging_contracts.events import HelloWorldEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand


@pytest.mark.asyncio
async def test_handle_hello_world_event_when_event_published(test_broker: TestRedisBroker) -> None:
    event = HelloWorldEvent(message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_message_class_path(message_class=HelloWorldEvent)}

    with patch("hello_world.messaging.handlers._logger") as mock_logger:
        await test_broker.publish(message=event, stream=HELLO_WORLD_STREAM, headers=headers)

        handle_hello_world_event.mock.assert_called_once()
        mock_logger.info.assert_called_once_with("Received HelloWorldEvent: %s", event)


@pytest.mark.asyncio
async def test_handle_hello_world_async_command_when_command_published(test_broker: TestRedisBroker) -> None:
    command = HelloWorldAsyncCommand(greeting="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_message_class_path(message_class=HelloWorldAsyncCommand)}

    with patch("hello_world.messaging.handlers._logger") as mock_logger:
        await test_broker.publish(message=command, stream=HELLO_WORLD_STREAM, headers=headers)

        handle_hello_world_async_command.mock.assert_called_once()
        mock_logger.info.assert_called_once_with("Received HelloWorldAsyncCommand: %s", command)
