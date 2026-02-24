from unittest.mock import patch

import pytest
from faststream.redis import TestRedisBroker
from libs.faststream_ext.utils import MESSAGE_CLASS_HEADER, get_message_class_path
from messaging_contracts.consts import WEARABLES_STREAM
from messaging_contracts.events import HelloWorldEvent
from wearables.messaging.handlers import handle_hello_world_event


@pytest.mark.asyncio
async def test_handle_hello_world_event_when_event_published(test_broker: TestRedisBroker) -> None:
    event = HelloWorldEvent(message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_message_class_path(message_class=HelloWorldEvent)}

    with patch("wearables.messaging.handlers._logger") as mock_logger:
        await test_broker.publish(message=event, stream=WEARABLES_STREAM, headers=headers)

        handle_hello_world_event.mock.assert_called_once()
        mock_logger.info.assert_called_once_with("Wearables received HelloWorldEvent: %s", event)
