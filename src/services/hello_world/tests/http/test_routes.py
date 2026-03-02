import pytest
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="session")
async def test_root_when_endpoint_hit(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/v1/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


@pytest.mark.asyncio(loop_scope="session")
async def test_health_when_service_running(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio(loop_scope="session")
async def test_readiness_check_when_service_running(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/readiness_check")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio(loop_scope="session")
async def test_get_host_when_endpoint_hit(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/v1/host")
    assert response.status_code == 200
    assert "host" in response.json()
