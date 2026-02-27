from logging import getLogger

from faststream import AckPolicy
from faststream.rabbit import RabbitQueue, RabbitRouter
from libs.faststream_ext import message_type_filter
from messaging_contracts.events import HelloWorldEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand
from rabbitmq_topology.entities import HELLO_WORLD_QUEUE

_logger = getLogger(__name__)

router = RabbitRouter()

_QUEUE = RabbitQueue(name=HELLO_WORLD_QUEUE.name, declare=False)

subscriber = router.subscriber(queue=_QUEUE, ack_policy=AckPolicy.ACK)


@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    _logger.info("Received HelloWorldEvent: %s", body)


@subscriber(filter=message_type_filter(HelloWorldAsyncCommand))
async def handle_hello_world_async_command(body: HelloWorldAsyncCommand) -> None:
    _logger.info("Received HelloWorldAsyncCommand: %s", body)
