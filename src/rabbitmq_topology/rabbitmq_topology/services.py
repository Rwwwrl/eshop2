from faststream.rabbit import RabbitExchange
from messaging_contracts.common import BaseMessage
from messaging_contracts.utils import get_message_full_class_path

from rabbitmq_topology.entities import EXCHANGES

_EXCHANGE_BY_NAME: dict[str, RabbitExchange] = {ex.name: ex for ex in EXCHANGES}


def get_exchange_for_message(message_class: type[BaseMessage]) -> RabbitExchange:
    class_path = get_message_full_class_path(message_class=message_class)
    try:
        return _EXCHANGE_BY_NAME[class_path]
    except KeyError:
        raise ValueError(f"No exchange defined for {class_path}. Add it to rabbitmq_topology/entities.py")
