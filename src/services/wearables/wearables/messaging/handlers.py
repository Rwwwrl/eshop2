from typing import Annotated

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
