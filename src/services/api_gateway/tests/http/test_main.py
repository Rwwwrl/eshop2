import pytest
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="session")
async def test_debug_error_when_endpoint_hit(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/v1/debug/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
