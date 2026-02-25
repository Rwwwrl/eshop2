import socket
from logging import getLogger

from faststream.middlewares import AckPolicy
from faststream.redis import RedisRouter, StreamSub
from libs.faststream_ext import message_type_filter
from messaging_contracts.consts import HELLO_WORLD_STREAM
from messaging_contracts.events import HelloWorldEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand

from hello_world.settings import settings

_logger = getLogger(__name__)

router = RedisRouter()


subscriber = router.subscriber(
    stream=StreamSub(
        HELLO_WORLD_STREAM,
        group="hello-world",
        consumer=socket.gethostname(),
        max_records=settings.faststream_max_records,
    ),
    ack_policy=AckPolicy.ACK,
)


@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    _logger.info("Received HelloWorldEvent: %s", body)


@subscriber(filter=message_type_filter(HelloWorldAsyncCommand))
async def handle_hello_world_async_command(body: HelloWorldAsyncCommand) -> None:
    _logger.info("Received HelloWorldAsyncCommand: %s", body)
