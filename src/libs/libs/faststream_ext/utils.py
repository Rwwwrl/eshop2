import json
from collections.abc import Callable

from faststream.rabbit import RabbitBroker, RabbitMessage
from messaging_contracts.common import BaseMessage
from rabbitmq_topology.services import publish as topology_publish

from libs.context_vars import request_id_var
from libs.faststream_ext.consts import REQUEST_ID_HEADER


def message_type_filter(message_class: type[BaseMessage]) -> Callable[[RabbitMessage], bool]:
    def _filter(msg: RabbitMessage) -> bool:
        return json.loads(msg.body).get("code") == message_class.code

    return _filter


async def publish(broker: RabbitBroker, message: BaseMessage) -> None:
    headers: dict[str, str] = {}

    request_id = request_id_var.get()
    if request_id is not None:
        headers[REQUEST_ID_HEADER] = request_id

    await topology_publish(broker=broker, message=message, headers=headers)
