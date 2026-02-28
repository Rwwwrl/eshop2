from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from libs.taskiq_ext.exceptions import DuplicateTaskMessageError
from sqlalchemy.ext.asyncio import AsyncEngine
from taskiq import AsyncBroker
from wearables.background_tasks.tasks import hello_world_task
from wearables.schemas.task_messages import HelloWorldTaskMessage


@pytest.mark.asyncio(loop_scope="session")
async def test_hello_world_task_processes_message(taskiq_broker: AsyncBroker, sqlmodel_engine: AsyncEngine) -> None:
    message = HelloWorldTaskMessage(logical_id=uuid4())

    with patch("wearables.background_tasks.tasks.execute_business_logic", new_callable=AsyncMock) as mock_business:
        task = await hello_world_task.kiq(body=message)
        result = await task.wait_result()

        assert result.is_err is False
        mock_business.assert_called_once()


@pytest.mark.asyncio(loop_scope="session")
async def test_hello_world_task_raises_on_duplicate(taskiq_broker: AsyncBroker, sqlmodel_engine: AsyncEngine) -> None:
    logical_id = uuid4()
    message = HelloWorldTaskMessage(logical_id=logical_id)

    with patch("wearables.background_tasks.tasks.execute_business_logic", new_callable=AsyncMock) as mock_business:
        task = await hello_world_task.kiq(body=message)
        result = await task.wait_result()
        assert result.is_err is False

        task2 = await hello_world_task.kiq(body=message)
        result2 = await task2.wait_result()
        assert result2.is_err is True
        assert isinstance(result2.error, DuplicateTaskMessageError)
        mock_business.assert_called_once()
