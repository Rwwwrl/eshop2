# Testing Patterns

## Fixtures (conftest.py)

```python
from collections.abc import AsyncGenerator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from wearables.routes import router


@pytest_asyncio.fixture(scope="session")
async def fastapi_app() -> AsyncGenerator[FastAPI]:
    app = FastAPI()
    app.include_router(router=router)
    yield app


@pytest_asyncio.fixture(scope="session")
async def async_client(fastapi_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
```

## Complete Test Examples

### Simple GET endpoint

```python
@pytest.mark.asyncio(loop_scope="session")
async def test_health(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### POST with valid payload

```python
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
```

### Validation error — missing required field

```python
@pytest.mark.asyncio(loop_scope="session")
async def test_handle_webhook_when_missing_required_field(async_client: AsyncClient) -> None:
    payload = {
        "event_type": "provider.connection.created",
        "client_user_id": "client-user-123",
    }
    response = await async_client.post(url="/webhook", json=payload)
    assert response.status_code == 422
```

### Validation error — extra fields forbidden

```python
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
```

### Edge case — empty nested object

```python
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
```

## Mock Patterns

### Multiple mocks

```python
with (
    patch("path.to.ServiceA.method", return_value=result_a) as mock_a,
    patch("path.to.ServiceB.method", return_value=result_b) as mock_b,
):
    response = await async_client.post(...)

assert mock_a.call_count == 1
assert mock_b.call_args.kwargs["param"] == expected_value
```

### Async mock

```python
from unittest.mock import AsyncMock

with patch(
    "path.to.async_function",
    new_callable=AsyncMock,
    return_value=expected_result
) as mock_func:
    response = await async_client.get(...)
```

### Side effects

```python
with patch(
    "path.to.function",
    side_effect=[first_call_result, second_call_result]
) as mock_func:
    # First call returns first_call_result
    # Second call returns second_call_result
    ...
```

## Verifying Mock Calls

```python
mock_create_order.assert_called_once()

# Check specific arguments
call_kwargs = mock_create_order.call_args.kwargs
assert call_kwargs["user_id"] == test_user.id
assert call_kwargs["product_id"] == product_id

# Check call count
assert mock_func.call_count == 3
```
