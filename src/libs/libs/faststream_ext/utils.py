from collections.abc import Callable

from faststream.rabbit import RabbitBroker, RabbitMessage
from messaging_contracts.common import BaseMessage
from rabbitmq_topology.services import get_exchange_for_message

from libs.context_vars import request_id_var
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER, REQUEST_ID_HEADER
from libs.utils import get_class_full_path


def message_type_filter(message_class: type[BaseMessage]) -> Callable[[RabbitMessage], bool]:
    expected_path = get_class_full_path(cls=message_class)

    def _filter(msg: RabbitMessage) -> bool:
        return msg.headers[MESSAGE_CLASS_HEADER] == expected_path

    return _filter


async def publish(broker: RabbitBroker, message: BaseMessage) -> None:
    exchange = get_exchange_for_message(message_class=type(message))

    headers: dict[str, str] = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=type(message))}

    request_id = request_id_var.get()
    if request_id is not None:
        headers[REQUEST_ID_HEADER] = request_id

    await broker.publish(message=message, exchange=exchange, headers=headers)
