from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from faststream.rabbit import RabbitQueue
from messaging_contracts.common import BaseMessage
from messaging_contracts.events import HelloWorldEvent
from rabbitmq_topology.resources import HELLO_WORLD_EVENT_EXCHANGE, HELLO_WORLD_QUEUE
from rabbitmq_topology.services import publish, publish_to_delayed_retry_queue
from rabbitmq_topology.utils import get_delayed_retry_queue_name, get_exchange_for_message


class _UnregisteredMessage(BaseMessage):
    pass


def test_get_exchange_for_message_when_message_class_is_registered() -> None:
    exchange = get_exchange_for_message(message_class=HelloWorldEvent)

    assert exchange is HELLO_WORLD_EVENT_EXCHANGE


def test_get_exchange_for_message_when_message_class_is_not_registered() -> None:
    with pytest.raises(ValueError, match="No exchange defined for"):
        get_exchange_for_message(message_class=_UnregisteredMessage)


def test_get_delayed_retry_queue_name_for_registered_queue() -> None:
    result = get_delayed_retry_queue_name(queue=HELLO_WORLD_QUEUE)

    assert result == "hello-world.delayed-retry"


def test_get_delayed_retry_queue_name_for_unregistered_queue() -> None:
    unregistered = RabbitQueue(name="unknown-queue")

    with pytest.raises(ValueError, match="No delayed-retry queue defined for 'unknown-queue'"):
        get_delayed_retry_queue_name(queue=unregistered)


@pytest.mark.asyncio(loop_scope="session")
async def test_publish_resolves_exchange_and_delegates() -> None:
    broker = AsyncMock()
    message = HelloWorldEvent(logical_id=uuid4(), message="test")
    headers = {"x-message-class": "messaging_contracts.events.HelloWorldEvent"}

    await publish(broker=broker, message=message, headers=headers)

    broker.publish.assert_called_once_with(
        message=message,
        exchange=HELLO_WORLD_EVENT_EXCHANGE,
        headers=headers,
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_publish_to_delayed_retry_queue_sends_to_correct_queue() -> None:
    broker = AsyncMock()
    rabbit_message = MagicMock()
    rabbit_message.body = b'{"message": "test"}'
    rabbit_message.headers = {"x-message-class": "messaging_contracts.events.HelloWorldEvent", "X-Request-ID": "abc"}
    extra_headers = {"x-retry-attempt": "1"}

    await publish_to_delayed_retry_queue(
        broker=broker,
        message=rabbit_message,
        original_queue=HELLO_WORLD_QUEUE,
        extra_headers=extra_headers,
        expiration=5,
    )

    broker.publish.assert_called_once_with(
        message=rabbit_message.body,
        exchange="",
        routing_key="hello-world.delayed-retry",
        headers={**rabbit_message.headers, **extra_headers},
        expiration=5,
    )
