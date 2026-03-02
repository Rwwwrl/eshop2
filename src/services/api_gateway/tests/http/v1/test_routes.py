from unittest.mock import AsyncMock, patch

import httpx
import pytest
from faststream.rabbit import TestRabbitBroker
from httpx import AsyncClient
from rabbitmq_topology.resources import (
    HELLO_WORLD_ASYNC_COMMAND_EXCHANGE,
    HELLO_WORLD_EVENT_EXCHANGE,
    OPEN_HEALTH_RESULT_RECEIVED_EVENT_EXCHANGE,
)


@pytest.mark.asyncio(loop_scope="session")
async def test_root_when_called(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/v1/")
    assert response.status_code == 200
    assert response.json() == {"message": "API Gateway"}


@pytest.mark.asyncio(loop_scope="session")
async def test_get_hello_world_host_when_called(async_client: AsyncClient) -> None:
    mock_response = httpx.Response(status_code=200, json={"host": "test-host"})

    with patch.object(
        httpx.AsyncClient,
        "get",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await async_client.get(url="/v1/hello-world/host")

    assert response.status_code == 200
    assert response.json() == {"host": "test-host"}


@pytest.mark.asyncio(loop_scope="session")
async def test_publish_hello_world_when_called(async_client: AsyncClient, test_broker: TestRabbitBroker) -> None:
    with patch.object(test_broker, "publish", new_callable=AsyncMock) as publish_mock:
        response = await async_client.post(url="/v1/debug/publish-hello-world")

    assert response.status_code == 202
    assert response.json() == {"status": "published"}

    assert publish_mock.call_count == 1
    assert publish_mock.call_args_list[0].kwargs["exchange"] == HELLO_WORLD_EVENT_EXCHANGE


@pytest.mark.asyncio(loop_scope="session")
async def test_publish_hello_world_async_command_when_called(
    async_client: AsyncClient, test_broker: TestRabbitBroker
) -> None:
    with patch.object(test_broker, "publish", new_callable=AsyncMock) as publish_mock:
        response = await async_client.post(url="/v1/debug/publish-hello-world-async-command")

    assert response.status_code == 202
    assert response.json() == {"status": "published"}

    assert publish_mock.call_count == 1
    assert publish_mock.call_args_list[0].kwargs["exchange"] == HELLO_WORLD_ASYNC_COMMAND_EXCHANGE


@pytest.mark.asyncio(loop_scope="session")
async def test_open_health_result_webhook_when_called(async_client: AsyncClient, test_broker: TestRabbitBroker) -> None:
    with patch.object(test_broker, "publish", new_callable=AsyncMock) as publish_mock:
        response = await async_client.post(url="/v1/open-health/result-webhook", json={"result_id": 123})

    assert response.status_code == 202
    assert response.content == b""

    assert publish_mock.call_count == 1
    assert publish_mock.call_args_list[0].kwargs["exchange"] == OPEN_HEALTH_RESULT_RECEIVED_EVENT_EXCHANGE
