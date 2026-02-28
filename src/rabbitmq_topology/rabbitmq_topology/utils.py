from faststream.rabbit import RabbitExchange, RabbitQueue
from messaging_contracts.common import BaseMessage


def get_exchange_name(message_class: type[BaseMessage]) -> str:
    return f"msg-{message_class.code}"


def get_exchange_for_message(message_class: type[BaseMessage]) -> RabbitExchange:
    from rabbitmq_topology.resources import EXCHANGE_BY_NAME

    exchange_name = get_exchange_name(message_class=message_class)
    try:
        return EXCHANGE_BY_NAME[exchange_name]
    except KeyError as exc:
        raise ValueError(f"No exchange defined for {exchange_name}. Add it to rabbitmq_topology/resources.py") from exc


def get_delayed_retry_queue_name(queue: RabbitQueue) -> str:
    from rabbitmq_topology.resources import DELAYED_RETRY_QUEUE_BY_ORIGINAL

    try:
        return DELAYED_RETRY_QUEUE_BY_ORIGINAL[queue.name]
    except KeyError as exc:
        raise ValueError(
            f"No delayed-retry queue defined for '{queue.name}'. Add it to rabbitmq_topology/resources.py"
        ) from exc
