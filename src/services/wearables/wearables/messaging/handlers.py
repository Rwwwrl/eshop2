from typing import Annotated

from taskiq import Context, TaskiqDepends

from wearables.messaging.main import broker


@broker.task(retry_on_error=True, max_retries=3)
async def hello_world_task(context: Annotated[Context, TaskiqDepends()]) -> str:
    retries = int(context.message.labels.get("_retries", 0))
    if retries < 2:
        raise RuntimeError(f"Simulated failure on attempt {retries + 1}")
    return "Hello from TaskIQ!"
