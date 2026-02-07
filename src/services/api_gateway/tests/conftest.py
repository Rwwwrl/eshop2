from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from api_gateway.routes import router
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from libs.fastapi_ext.middlewares import UnhandledExceptionMiddleware


@pytest.fixture()
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.add_middleware(UnhandledExceptionMiddleware)
    test_app.include_router(router=router)
    return test_app


@pytest_asyncio.fixture()
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
