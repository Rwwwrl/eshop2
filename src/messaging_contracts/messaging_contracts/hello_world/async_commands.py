from libs.faststream_ext import AsyncCommand, streams

from messaging_contracts.consts import HELLO_WORLD_STREAM


@streams(HELLO_WORLD_STREAM)
class HelloWorldAsyncCommand(AsyncCommand):
    greeting: str
