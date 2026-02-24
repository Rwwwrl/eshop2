import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.responses import Response
from httpx import AsyncClient
from libs.taskiq_ext.health_server import HealthServer


@pytest_asyncio.fixture(scope="session")
async def health_server() -> AsyncGenerator[HealthServer]:
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)

    @app.get("/health-check", status_code=204)
    async def health_check() -> Response:
        return Response(status_code=204)

    server = HealthServer(app=app, port=19876)
    await server.start()
    # NOTE @sosov: uvicorn starts in a background task — sleep gives it time to bind the socket.
    await asyncio.sleep(0.1)

    yield server

    await server.stop()


@pytest.mark.asyncio(loop_scope="session")
async def test_health_server_serves_requests(health_server: HealthServer) -> None:
    async with AsyncClient() as client:
        response = await client.get(url="http://127.0.0.1:19876/health-check")

    assert response.status_code == 204


@pytest.mark.asyncio(loop_scope="session")
async def test_health_server_returns_404_for_unknown_path(health_server: HealthServer) -> None:
    async with AsyncClient() as client:
        response = await client.get(url="http://127.0.0.1:19876/unknown")

    assert response.status_code == 404
