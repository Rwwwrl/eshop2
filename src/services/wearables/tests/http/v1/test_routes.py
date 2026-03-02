import pytest
from httpx import AsyncClient
from libs.sqlmodel_ext import Session
from sqlalchemy import select
from wearables.models import WearableEvent


@pytest.mark.asyncio(loop_scope="session")
async def test_kiq_hello_world_when_called(async_client: AsyncClient) -> None:
    response = await async_client.post(url="/v1/debug/kiq-hello-world")
    assert response.status_code == 202
    assert "task_id" in response.json()


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_valid_payload(async_client: AsyncClient) -> None:
    payload = {
        "user_id": 1,
        "biomarker_name": "heart_rate",
        "value": 72.5,
        "timestamp": "2025-02-11T10:00:00Z",
    }

    response = await async_client.post(url="/v1/webhook", json=payload)

    assert response.status_code == 201

    async with Session() as session, session.begin():
        result = await session.execute(select(WearableEvent))
        events = result.scalars().all()
        assert len(events) == 1
        assert events[0].user_id == 1
        assert events[0].biomarker_name == "heart_rate"
        assert events[0].value == 72.5


@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_missing_required_field(async_client: AsyncClient) -> None:
    payload = {
        "user_id": 1,
        "biomarker_name": "heart_rate",
    }

    response = await async_client.post(url="/v1/webhook", json=payload)

    assert response.status_code == 422
