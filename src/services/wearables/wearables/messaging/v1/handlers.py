from faststream import AckPolicy
from faststream.rabbit import RabbitQueue, RabbitRouter
from libs.faststream_ext import message_type_filter
from libs.faststream_ext.exceptions import DuplicateMessageError
from libs.faststream_ext.repositories import ProcessedMessageRepository
from libs.sqlmodel_ext import Session
from libs.utils import execute_business_logic
from messaging_contracts.v1.events import HelloWorldEvent
from rabbitmq_topology.resources import WEARABLES_QUEUE
from sqlalchemy.exc import IntegrityError

router = RabbitRouter()

_QUEUE = RabbitQueue(name=WEARABLES_QUEUE.name, declare=False)

subscriber = router.subscriber(queue=_QUEUE, ack_policy=AckPolicy.ACK)


@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    async with Session() as session, session.begin():
        try:
            await ProcessedMessageRepository.save(
                session=session,
                logical_id=body.logical_id,
                message_code=body.code,
            )
        except IntegrityError as exc:
            raise DuplicateMessageError from exc

        await execute_business_logic(session=session, body=body)
