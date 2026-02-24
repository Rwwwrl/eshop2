from logging import getLogger

from faststream.redis import RedisRouter
from libs.faststream_ext import message_type_filter
from messaging_contracts.consts import HELLO_WORLD_STREAM
from messaging_contracts.events import HelloWorldEvent

_logger = getLogger(__name__)

router = RedisRouter()


@router.subscriber(stream=HELLO_WORLD_STREAM, filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: dict) -> None:
    _logger.info("Received HelloWorldEvent: %s", body)
