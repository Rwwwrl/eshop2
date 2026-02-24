from logging import getLogger

from faststream.middlewares import AckPolicy
from faststream.redis import RedisRouter, StreamSub
from libs.faststream_ext import message_type_filter
from messaging_contracts.consts import WEARABLES_STREAM
from messaging_contracts.events import HelloWorldEvent

from wearables.settings import settings

_logger = getLogger(__name__)

router = RedisRouter()


subscriber = router.subscriber(
    stream=StreamSub(WEARABLES_STREAM, max_records=settings.faststream_max_records),
    ack_policy=AckPolicy.ACK,
)


@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    _logger.info("Wearables received HelloWorldEvent: %s", body)
