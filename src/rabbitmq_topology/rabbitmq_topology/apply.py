import asyncio
import os

from faststream.rabbit import RabbitBroker

from rabbitmq_topology.entities import BINDINGS, DEAD_LETTER_QUEUES, EXCHANGES, QUEUES


async def apply_topology(amqp_url: str) -> None:
    broker = RabbitBroker(url=amqp_url)
    await broker.connect()

    try:
        declared_exchanges = {}
        for rabbit_exchange in EXCHANGES:
            declared_exchanges[rabbit_exchange.name] = await broker.declare_exchange(rabbit_exchange)

        declared_queues = {}
        for rabbit_queue in DEAD_LETTER_QUEUES:
            declared_queues[rabbit_queue.name] = await broker.declare_queue(rabbit_queue)

        for rabbit_queue in QUEUES:
            declared_queues[rabbit_queue.name] = await broker.declare_queue(rabbit_queue)

        for binding in BINDINGS:
            for queue in binding.queues:
                await declared_queues[queue.name].bind(
                    exchange=declared_exchanges[binding.exchange.name],
                )
    finally:
        await broker.stop()


if __name__ == "__main__":
    asyncio.run(apply_topology(amqp_url=os.environ["RABBITMQ_URL"]))
