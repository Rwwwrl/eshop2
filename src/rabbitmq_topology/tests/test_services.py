import pytest
from messaging_contracts.common import BaseMessage
from messaging_contracts.events import HelloWorldEvent
from rabbitmq_topology.entities import HELLO_WORLD_EVENT_EXCHANGE
from rabbitmq_topology.services import get_exchange_for_message


class _UnregisteredMessage(BaseMessage):
    pass


@pytest.mark.asyncio(loop_scope="session")
async def test_get_exchange_for_message_when_message_class_is_registered() -> None:
    exchange = get_exchange_for_message(message_class=HelloWorldEvent)

    assert exchange is HELLO_WORLD_EVENT_EXCHANGE


@pytest.mark.asyncio(loop_scope="session")
async def test_get_exchange_for_message_when_message_class_is_not_registered() -> None:
    with pytest.raises(ValueError, match="No exchange defined for"):
        get_exchange_for_message(message_class=_UnregisteredMessage)
