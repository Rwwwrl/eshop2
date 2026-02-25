from unittest.mock import AsyncMock, patch

import httpx
import pytest
from faststream.redis import TestRedisBroker
from httpx import AsyncClient
from messaging_contracts.consts import HELLO_WORLD_STREAM, WEARABLES_STREAM


@pytest.mark.asyncio
async def test_root_when_called(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/")
    assert response.status_code == 200
    assert response.json() == {"message": "API Gateway"}


@pytest.mark.asyncio
async def test_health_when_called(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_check_when_called(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/readiness_check")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_get_hello_world_host_when_called(async_client: AsyncClient) -> None:
    mock_response = httpx.Response(status_code=200, json={"host": "test-host"})

    with patch.object(
        httpx.AsyncClient,
        "get",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        response = await async_client.get(url="/hello-world/host")

    assert response.status_code == 200
    assert response.json() == {"host": "test-host"}


@pytest.mark.asyncio
async def test_publish_hello_world_when_called(async_client: AsyncClient, test_broker: TestRedisBroker) -> None:
    with patch.object(test_broker, "publish", wraps=test_broker.publish) as publish_spy:
        response = await async_client.post(url="/debug/publish-hello-world")

    assert response.status_code == 202
    assert response.json() == {"status": "published"}

    assert publish_spy.call_count == 2
    published_streams = {call.kwargs["stream"] for call in publish_spy.call_args_list}
    assert published_streams == {HELLO_WORLD_STREAM, WEARABLES_STREAM}


@pytest.mark.asyncio
async def test_publish_hello_world_async_command_when_called(
    async_client: AsyncClient, test_broker: TestRedisBroker
) -> None:
    with patch.object(test_broker, "publish", wraps=test_broker.publish) as publish_spy:
        response = await async_client.post(url="/debug/publish-hello-world-async-command")

    assert response.status_code == 202
    assert response.json() == {"status": "published"}

    assert publish_spy.call_count == 1
    assert publish_spy.call_args_list[0].kwargs["stream"] == HELLO_WORLD_STREAM
