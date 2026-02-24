from collections.abc import Callable

from faststream.redis import RedisBroker, RedisMessage

from libs.context_vars import request_id_var
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER, REQUEST_ID_HEADER
from libs.faststream_ext.schemas.dtos import BaseMessage


def get_message_class_path(message_class: type[BaseMessage]) -> str:
    return f"{message_class.__module__}.{message_class.__qualname__}"


def message_type_filter(message_class: type[BaseMessage]) -> Callable[[RedisMessage], bool]:
    expected_path = get_message_class_path(message_class=message_class)

    def _filter(msg: RedisMessage) -> bool:
        return msg.headers[MESSAGE_CLASS_HEADER] == expected_path

    return _filter


async def publish(broker: RedisBroker, message: BaseMessage) -> None:
    if not message.__streams__:
        raise TypeError(f"{type(message).__name__} has no streams. Apply @streams decorator.")

    class_path = get_message_class_path(message_class=type(message))
    headers: dict[str, str] = {MESSAGE_CLASS_HEADER: class_path}

    request_id = request_id_var.get()
    if request_id is not None:
        headers[REQUEST_ID_HEADER] = request_id

    for stream in message.__streams__:
        await broker.publish(message=message, stream=stream, headers=headers)
