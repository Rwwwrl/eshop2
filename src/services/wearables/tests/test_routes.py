import pytest
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="session")
async def test_health(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio(loop_scope="session")
async def test_readiness_check(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/readiness_check")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_valid_payload(async_client: AsyncClient) -> None:
    payload = {
        "event_type": "provider.connection.created",
        "client_user_id": "client-user-123",
        "user_id": "junction-user-456",
        "data": {"provider": "oura", "status": "connected"},
    }
    response = await async_client.post(url="/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_missing_required_field(async_client: AsyncClient) -> None:
    payload = {
        "event_type": "provider.connection.created",
        "client_user_id": "client-user-123",
    }
    response = await async_client.post(url="/webhook", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_extra_fields_forbidden(async_client: AsyncClient) -> None:
    payload = {
        "event_type": "historical.data.sleep.created",
        "client_user_id": "client-user-123",
        "user_id": "junction-user-456",
        "data": {"some": "data"},
        "unknown_future_field": "should cause error",
    }
    response = await async_client.post(url="/webhook", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_empty_data_dict(async_client: AsyncClient) -> None:
    payload = {
        "event_type": "daily.data.activity.created",
        "client_user_id": "client-user-123",
        "user_id": "junction-user-456",
        "data": {},
    }
    response = await async_client.post(url="/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
