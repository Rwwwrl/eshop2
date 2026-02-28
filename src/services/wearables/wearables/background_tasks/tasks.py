import asyncio
import time
from logging import getLogger

from libs.sqlmodel_ext import Session
from libs.taskiq_ext.exceptions import DuplicateTaskMessageError
from libs.taskiq_ext.repositories import ProcessedTaskMessageRepository
from libs.utils import execute_business_logic
from sqlalchemy.exc import IntegrityError
from taskiq.brokers.shared_broker import async_shared_broker

from wearables.schemas.task_messages import HelloWorldTaskMessage

_logger = getLogger(__name__)


@async_shared_broker.task(retry_on_error=True, max_retries=3)
async def hello_world_task(body: HelloWorldTaskMessage) -> None:
    _logger.info("hello_world_task started")
    async with Session() as session, session.begin():
        try:
            await ProcessedTaskMessageRepository.save(
                session=session,
                logical_id=body.logical_id,
                task_message_code=body.code,
            )
        except IntegrityError as exc:
            raise DuplicateTaskMessageError from exc

        await execute_business_logic(session=session, body=body)
    _logger.info("hello_world_task completed successfully")


@async_shared_broker.task()
async def process_5_min_batch() -> None:
    await asyncio.to_thread(time.sleep, 1)


@async_shared_broker.task(schedule=[{"cron": "*/10 * * * *"}])
async def dispatch_wearable_events() -> None:
    await asyncio.gather(*(process_5_min_batch.kiq() for _ in range(10)))
