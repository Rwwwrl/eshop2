import asyncio
import time
from logging import getLogger
from typing import Annotated
from uuid import uuid4

from libs.sqlmodel_ext.utils import health_check as postgres_health_check
from taskiq import Context, TaskiqDepends
from taskiq.brokers.shared_broker import async_shared_broker

_logger = getLogger(__name__)


@async_shared_broker.task(retry_on_error=True, max_retries=3)
async def hello_world_task(context: Annotated[Context, TaskiqDepends()]) -> str:
    _logger.info("hello_world_task started")
    await postgres_health_check()
    retries = int(context.message.labels.get("_retries", 0))
    if retries < 2:
        raise RuntimeError(f"Simulated failure on attempt {retries + 1}")
    _logger.info("hello_world_task completed successfully")
    return "Hello from TaskIQ!"


@async_shared_broker.task()
async def process_5_min_batch() -> str:
    await asyncio.to_thread(time.sleep, 1)
    return f"foo {uuid4()}"


@async_shared_broker.task(schedule=[{"cron": "*/10 * * * *"}])
async def dispatch_wearable_events() -> str:
    await asyncio.gather(*(process_5_min_batch.kiq() for _ in range(10)))
    return "Dispatched 10 tasks"
