from faststream import AckPolicy
from faststream.rabbit import RabbitQueue, RabbitRouter
from faststream.rabbit.annotations import ContextRepo as ContextRepoDep
from libs.faststream_ext import message_type_filter
from libs.faststream_ext.exceptions import DuplicateMessageError
from libs.faststream_ext.rabbitmq_ext.decorators import retry
from libs.faststream_ext.repositories import ProcessedMessageRepository
from libs.sqlmodel_ext import Session
from libs.utils import execute_business_logic
from messaging_contracts.events import HelloWorldEvent, OpenHealthResultReceivedEvent
from messaging_contracts.hello_world.async_commands import HelloWorldAsyncCommand
from rabbitmq_topology.resources import HELLO_WORLD_QUEUE
from sqlalchemy.exc import IntegrityError

router = RabbitRouter()

_QUEUE = RabbitQueue(name=HELLO_WORLD_QUEUE.name, declare=False)

subscriber = router.subscriber(queue=_QUEUE, ack_policy=AckPolicy.ACK)


@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    async with Session() as session, session.begin():
        try:
            await ProcessedMessageRepository.save(session=session, logical_id=body.logical_id)
        except IntegrityError as exc:
            raise DuplicateMessageError from exc

        await execute_business_logic(session=session, body=body)


@subscriber(filter=message_type_filter(HelloWorldAsyncCommand))
async def handle_hello_world_async_command(body: HelloWorldAsyncCommand) -> None:
    async with Session() as session, session.begin():
        try:
            await ProcessedMessageRepository.save(session=session, logical_id=body.logical_id)
        except IntegrityError as exc:
            raise DuplicateMessageError from exc

        await execute_business_logic(session=session, body=body)


@subscriber(filter=message_type_filter(OpenHealthResultReceivedEvent))
@retry(max_attempts=3, countdown=5, dlq=True)
async def handle_open_health_result_received(body: OpenHealthResultReceivedEvent, context: ContextRepoDep) -> None:
    async with Session() as session, session.begin():
        try:
            await ProcessedMessageRepository.save(session=session, logical_id=body.logical_id)
        except IntegrityError as exc:
            raise DuplicateMessageError from exc

        await execute_business_logic(session=session, body=body)
        raise RuntimeError("Simulated failure for retry test")
