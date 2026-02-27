from faststream.rabbit import RabbitExchange, RabbitQueue
from messaging_contracts.common import BaseMessage
from messaging_contracts.utils import get_message_full_class_path

from rabbitmq_topology.resources import DELAYED_RETRY_QUEUES, EXCHANGES

_EXCHANGE_BY_NAME: dict[str, RabbitExchange] = {ex.name: ex for ex in EXCHANGES}

_DELAYED_RETRY_QUEUE_BY_ORIGINAL: dict[str, str] = {
    q.arguments["x-dead-letter-routing-key"]: q.name for q in DELAYED_RETRY_QUEUES
}


def get_exchange_for_message(message_class: type[BaseMessage]) -> RabbitExchange:
    class_path = get_message_full_class_path(message_class=message_class)
    try:
        return _EXCHANGE_BY_NAME[class_path]
    except KeyError as exc:
        raise ValueError(f"No exchange defined for {class_path}. Add it to rabbitmq_topology/resources.py") from exc


def get_delayed_retry_queue_name(queue: RabbitQueue) -> str:
    try:
        return _DELAYED_RETRY_QUEUE_BY_ORIGINAL[queue.name]
    except KeyError as exc:
        raise ValueError(
            f"No delayed-retry queue defined for '{queue.name}'. Add it to rabbitmq_topology/resources.py"
        ) from exc
