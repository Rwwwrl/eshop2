from aio_pika import DeliveryMode
from faststream.rabbit import RabbitBroker, RabbitMessage, RabbitQueue
from messaging_contracts.common import BaseMessage

from rabbitmq_topology.utils import get_delayed_retry_queue_name, get_exchange_for_message


async def publish(broker: RabbitBroker, message: BaseMessage, headers: dict[str, str]) -> None:
    exchange = get_exchange_for_message(message_class=type(message))
    await broker.publish(message=message, exchange=exchange, headers=headers, persist=message.persistent)


async def publish_to_delayed_retry_queue(
    broker: RabbitBroker,
    message: RabbitMessage,
    original_queue: RabbitQueue,
    extra_headers: dict[str, str],
    expiration: int,
) -> None:
    persist = message.raw_message.delivery_mode == DeliveryMode.PERSISTENT

    await broker.publish(
        message=message.body,
        headers={**message.headers, **extra_headers},
        exchange="",
        routing_key=get_delayed_retry_queue_name(queue=original_queue),
        expiration=expiration,
        persist=persist,
    )
