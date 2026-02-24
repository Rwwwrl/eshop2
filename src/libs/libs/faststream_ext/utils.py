from collections.abc import Callable

from faststream.redis import RedisBroker, RedisMessage

from libs.faststream_ext.schemas.dtos import BaseMessage

_MESSAGE_CLASS_HEADER = "x-message-class"


def _get_message_class_path(message_class: type[BaseMessage]) -> str:
    return f"{message_class.__module__}.{message_class.__qualname__}"


def message_type_filter(message_class: type[BaseMessage]) -> Callable[[RedisMessage], bool]:
    expected_path = _get_message_class_path(message_class=message_class)

    def _filter(msg: RedisMessage) -> bool:
        return msg.headers[_MESSAGE_CLASS_HEADER] == expected_path

    return _filter


async def publish(broker: RedisBroker, message: BaseMessage) -> None:
    class_path = _get_message_class_path(message_class=type(message))
    headers = {_MESSAGE_CLASS_HEADER: class_path}
    for stream in message.__streams__:
        await broker.publish(message=message, stream=stream, headers=headers)
