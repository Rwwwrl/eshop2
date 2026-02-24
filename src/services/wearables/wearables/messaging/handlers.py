from logging import getLogger

from faststream.redis import RedisRouter
from libs.faststream_ext import message_type_filter
from messaging_contracts.consts import WEARABLES_STREAM
from messaging_contracts.events import HelloWorldEvent

_logger = getLogger(__name__)

router = RedisRouter()


subscriber = router.subscriber(stream=WEARABLES_STREAM)


@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    _logger.info("Wearables received HelloWorldEvent: %s", body)
