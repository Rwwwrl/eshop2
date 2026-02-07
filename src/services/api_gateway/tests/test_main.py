import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_debug_error_returns_500(async_client: AsyncClient) -> None:
    response = await async_client.get("/debug/error")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
