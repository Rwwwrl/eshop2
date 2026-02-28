from faststream.rabbit import RabbitExchange, RabbitQueue
from faststream.rabbit.schemas import ExchangeType
from messaging_contracts.events import HelloWorldEvent, OpenHealthResultReceivedEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand

from rabbitmq_topology.consts import SEVEN_DAYS_IN_MS, THREE_DAYS_IN_MS
from rabbitmq_topology.schemas.dtos import RabbitBinding
from rabbitmq_topology.utils import get_exchange_name

HELLO_WORLD_EVENT_EXCHANGE = RabbitExchange(
    name=get_exchange_name(message_class=HelloWorldEvent),
    type=ExchangeType.FANOUT,
    durable=True,
)
HELLO_WORLD_ASYNC_COMMAND_EXCHANGE = RabbitExchange(
    name=get_exchange_name(message_class=HelloWorldAsyncCommand),
    type=ExchangeType.FANOUT,
    durable=True,
)

OPEN_HEALTH_RESULT_RECEIVED_EVENT_EXCHANGE = RabbitExchange(
    name=get_exchange_name(message_class=OpenHealthResultReceivedEvent),
    type=ExchangeType.FANOUT,
    durable=True,
)

EXCHANGES: list[RabbitExchange] = [
    HELLO_WORLD_EVENT_EXCHANGE,
    HELLO_WORLD_ASYNC_COMMAND_EXCHANGE,
    OPEN_HEALTH_RESULT_RECEIVED_EVENT_EXCHANGE,
]

HELLO_WORLD_DLQ = RabbitQueue(
    name="hello-world.dlq",
    durable=True,
    arguments={"x-message-ttl": SEVEN_DAYS_IN_MS},
)
WEARABLES_DLQ = RabbitQueue(
    name="wearables.dlq",
    durable=True,
    arguments={"x-message-ttl": SEVEN_DAYS_IN_MS},
)

DEAD_LETTER_QUEUES: list[RabbitQueue] = [
    HELLO_WORLD_DLQ,
    WEARABLES_DLQ,
]

HELLO_WORLD_QUEUE = RabbitQueue(
    name="hello-world",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": HELLO_WORLD_DLQ.name,
        "x-message-ttl": THREE_DAYS_IN_MS,
    },
)
WEARABLES_QUEUE = RabbitQueue(
    name="wearables",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": WEARABLES_DLQ.name,
        "x-message-ttl": THREE_DAYS_IN_MS,
    },
)

QUEUES: list[RabbitQueue] = [
    HELLO_WORLD_QUEUE,
    WEARABLES_QUEUE,
]

HELLO_WORLD_DELAYED_RETRY = RabbitQueue(
    name=f"{HELLO_WORLD_QUEUE.name}.delayed-retry",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": HELLO_WORLD_QUEUE.name,
    },
)
WEARABLES_DELAYED_RETRY = RabbitQueue(
    name=f"{WEARABLES_QUEUE.name}.delayed-retry",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": WEARABLES_QUEUE.name,
    },
)

DELAYED_RETRY_QUEUES: list[RabbitQueue] = [
    HELLO_WORLD_DELAYED_RETRY,
    WEARABLES_DELAYED_RETRY,
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
    RabbitBinding(
        exchange=OPEN_HEALTH_RESULT_RECEIVED_EVENT_EXCHANGE,
        queues=[HELLO_WORLD_QUEUE],
    ),
]

EXCHANGE_BY_NAME: dict[str, RabbitExchange] = {ex.name: ex for ex in EXCHANGES}

DELAYED_RETRY_QUEUE_BY_ORIGINAL: dict[str, str] = {
    q.arguments["x-dead-letter-routing-key"]: q.name for q in DELAYED_RETRY_QUEUES
}
