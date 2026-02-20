import asyncio
import time
from typing import Annotated
from uuid import uuid4

from libs.sqlmodel_ext.utils import health_check as postgres_health_check
from taskiq import Context, TaskiqDepends
from taskiq.brokers.shared_broker import async_shared_broker


@async_shared_broker.task(retry_on_error=True, max_retries=3)
async def hello_world_task(context: Annotated[Context, TaskiqDepends()]) -> str:
    await postgres_health_check()
    retries = int(context.message.labels.get("_retries", 0))
    if retries < 2:
        raise RuntimeError(f"Simulated failure on attempt {retries + 1}")
    return "Hello from TaskIQ!"


@async_shared_broker.task()
async def process_5_min_batch() -> str:
    time.sleep(1)
    return f"foo {uuid4()}"


@async_shared_broker.task(schedule=[{"cron": "*/5 * * * *"}])
async def dispatch_wearable_events() -> str:
    sem = asyncio.Semaphore(200)

    async def _kick() -> None:
        async with sem:
            await process_5_min_batch.kiq()

    async with asyncio.TaskGroup() as tg:
        for _ in range(1500):
            tg.create_task(_kick())

    return "Dispatched 1500 tasks"
