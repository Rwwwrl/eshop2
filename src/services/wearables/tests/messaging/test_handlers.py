import pytest
from taskiq import AsyncBroker
from wearables.messaging.handlers import hello_world_task


@pytest.mark.asyncio
async def test_hello_world_task(taskiq_broker: AsyncBroker) -> None:
    task = await hello_world_task.kiq()
    result = await task.wait_result()
    assert result.return_value == "Hello from TaskIQ!"
