from unittest.mock import AsyncMock, patch

import httpx
import pytest
from httpx import AsyncClient


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
