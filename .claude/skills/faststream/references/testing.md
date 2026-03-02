# FastStream Testing

`TestRabbitBroker` provides in-memory testing — no real RabbitMQ needed.

## Fixture

```python
# conftest.py
from faststream.rabbit import TestRabbitBroker
from <service>.messaging.main import broker as faststream_broker

@pytest_asyncio.fixture(scope="function")
async def test_broker() -> AsyncGenerator[TestRabbitBroker]:
    async with TestRabbitBroker(faststream_broker) as br:
        yield br
```

## Handler Tests

```python
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from libs.faststream_ext.exceptions import DuplicateMessageError
from rabbitmq_topology.resources import HELLO_WORLD_QUEUE
from sqlalchemy.ext.asyncio import AsyncEngine

async def test_handle_hello_world_event(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    event = HelloWorldEvent(logical_id=uuid4(), message="Hello from test!")

    with patch("hello_world.messaging.v1.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)

        handle_hello_world_event.mock.assert_called_once()
        mock_business.assert_called_once()
```

## Duplicate Rejection Tests

```python
async def test_handle_hello_world_event_when_duplicate_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    logical_id = uuid4()
    event = HelloWorldEvent(logical_id=logical_id, message="Hello from test!")

    with patch("hello_world.messaging.v1.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)

        with pytest.raises(DuplicateMessageError):
            await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name)

        mock_business.assert_called_once()  # business logic ran only on first delivery
```

## Publisher Tests

```python
async def test_publish_event(async_client: AsyncClient, test_broker: TestRabbitBroker) -> None:
    with patch.object(test_broker, "publish", wraps=test_broker.publish) as publish_spy:
        response = await async_client.post(url="/debug/publish-hello-world")

    assert publish_spy.call_count == 1
    assert publish_spy.call_args_list[0].kwargs["exchange"] == HELLO_WORLD_EVENT_EXCHANGE
```

## Test Rules

- Publish to the **queue** in tests — `TestRabbitBroker` doesn't simulate exchange routing
- No headers needed — `message_type_filter()` reads `code` from the serialized message body
- Queue name from topology: `HELLO_WORLD_QUEUE.name`, `WEARABLES_QUEUE.name`
- Handler gains `.mock` attribute inside `TestRabbitBroker` context
- Always pass `logical_id=uuid4()` when constructing messages in tests
- Handler tests require `sqlmodel_engine: AsyncEngine` fixture (DB needed for `ProcessedMessage`)
- Duplicate tests: publish same `logical_id` twice, assert `DuplicateMessageError` on second, assert business logic ran once
