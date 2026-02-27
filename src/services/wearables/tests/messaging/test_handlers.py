from unittest.mock import patch

import pytest
from faststream.rabbit import TestRabbitBroker
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER
from libs.utils import get_class_full_path
from messaging_contracts.events import HelloWorldEvent
from rabbitmq_topology.entities import WEARABLES_QUEUE
from wearables.messaging.handlers import handle_hello_world_event


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_hello_world_event_when_event_published(test_broker: TestRabbitBroker) -> None:
    event = HelloWorldEvent(message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    with patch("wearables.messaging.handlers._logger") as mock_logger:
        await test_broker.publish(message=event, queue=WEARABLES_QUEUE.name, headers=headers)

        handle_hello_world_event.mock.assert_called_once()
        mock_logger.info.assert_called_once_with("Wearables received HelloWorldEvent: %s", event)
