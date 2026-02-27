from logging import getLogger

from faststream import AckPolicy
from faststream.rabbit import RabbitQueue, RabbitRouter
from libs.faststream_ext import message_type_filter
from messaging_contracts.events import HelloWorldEvent
from rabbitmq_topology.entities import WEARABLES_QUEUE

_logger = getLogger(__name__)

router = RabbitRouter()

_QUEUE = RabbitQueue(name=WEARABLES_QUEUE.name, declare=False)

subscriber = router.subscriber(queue=_QUEUE, ack_policy=AckPolicy.ACK)


@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    _logger.info("Wearables received HelloWorldEvent: %s", body)
