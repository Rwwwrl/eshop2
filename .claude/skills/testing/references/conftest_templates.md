# conftest.py Templates

## Service conftest (no DB)

For services without database dependencies (api_gateway pattern):

```python
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from libs.fastapi_ext.middlewares import UnhandledExceptionMiddleware
from <service>.routes import router


@pytest.fixture(scope="session")
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(UnhandledExceptionMiddleware)
    test_app.include_router(router=router)
    return test_app


@pytest_asyncio.fixture(scope="session")
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
```

Key: session-scoped fixtures, no DB setup.

## Self-Contained Test File (libs pattern)

For lib tests without a shared conftest — define fixtures inline:

```python
import pytest
import pytest_asyncio
from collections.abc import AsyncGenerator
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

from libs.fastapi_ext.middlewares import SecurityHeadersMiddleware

_router = APIRouter()


@_router.get("/ok")
async def _ok() -> dict[str, str]:
    return {"status": "ok"}


@pytest.fixture(scope="session")
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(SecurityHeadersMiddleware)
    test_app.include_router(router=_router)
    return test_app


@pytest_asyncio.fixture(scope="session")
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio(loop_scope="session")
async def test_security_headers_present(async_client: AsyncClient) -> None:
    response = await async_client.get(url="/ok")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
```

Key: test-specific routes prefixed with `_`, all fixtures in the same file.

## DB Integration conftest (wearables pattern)

For services with PostgreSQL. Requires `-p libs.tests_ext.sqlmodel_fixtures` in pytest config.

```python
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from libs.sqlmodel_ext import BaseSqlModel
from sqlalchemy.ext.asyncio import AsyncEngine
from <service>.models import MyModel
from <service>.routes import router
from <service>.settings import settings as service_settings


@pytest.fixture(scope="session")
def settings() -> service_settings.__class__:
    return service_settings


@pytest.fixture(scope="session")
def autocleared_sqlmodel_tables() -> list[type[BaseSqlModel]]:
    return [MyModel]


@pytest_asyncio.fixture(scope="session")
async def fastapi_app(sqlmodel_engine: AsyncEngine) -> AsyncGenerator[FastAPI]:
    app = FastAPI()
    app.state.sqlmodel_engine = sqlmodel_engine
    app.include_router(router=router)
    yield app


@pytest_asyncio.fixture(scope="session")
async def async_client(fastapi_app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
```

Key differences from unit test conftest:
- **Session scope** for all fixtures
- `settings` fixture provides `PostgresSettingsMixin` for the shared `sqlmodel_engine`
- `autocleared_sqlmodel_tables` lists tables to TRUNCATE after each test
- `fastapi_app` depends on `sqlmodel_engine` (from shared plugin)
- Engine stored on `app.state.sqlmodel_engine`
- Named `fastapi_app` (not `app`) to avoid fixture name conflicts

## Test Examples

### POST with valid payload (success)

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

### POST with missing required field (validation error)

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
