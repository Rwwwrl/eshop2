from faststream.rabbit import RabbitExchange, RabbitQueue
from faststream.rabbit.schemas import ExchangeType
from messaging_contracts.events import HelloWorldEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand
from messaging_contracts.utils import get_message_full_class_path

from rabbitmq_topology.schemas.dtos import RabbitBinding

HELLO_WORLD_EVENT_EXCHANGE = RabbitExchange(
    name=get_message_full_class_path(message_class=HelloWorldEvent),
    type=ExchangeType.FANOUT,
)
HELLO_WORLD_ASYNC_COMMAND_EXCHANGE = RabbitExchange(
    name=get_message_full_class_path(message_class=HelloWorldAsyncCommand),
    type=ExchangeType.FANOUT,
)

EXCHANGES: list[RabbitExchange] = [
    HELLO_WORLD_EVENT_EXCHANGE,
    HELLO_WORLD_ASYNC_COMMAND_EXCHANGE,
]

HELLO_WORLD_QUEUE = RabbitQueue(name="hello-world")
WEARABLES_QUEUE = RabbitQueue(name="wearables")

QUEUES: list[RabbitQueue] = [
    HELLO_WORLD_QUEUE,
    WEARABLES_QUEUE,
]

BINDINGS: list[RabbitBinding] = [
    RabbitBinding(
        exchange=HELLO_WORLD_EVENT_EXCHANGE,
        queues=[HELLO_WORLD_QUEUE, WEARABLES_QUEUE],
    ),
    RabbitBinding(
        exchange=HELLO_WORLD_ASYNC_COMMAND_EXCHANGE,
        queues=[HELLO_WORLD_QUEUE],
    ),
]
