from libs.faststream_ext import Event, streams

from messaging_contracts.consts import HELLO_WORLD_STREAM, WEARABLES_STREAM


@streams(HELLO_WORLD_STREAM, WEARABLES_STREAM)
class HelloWorldEvent(Event):
    message: str
