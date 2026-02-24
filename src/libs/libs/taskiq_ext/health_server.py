import asyncio
import logging

import uvicorn
from fastapi import FastAPI

_logger = logging.getLogger(__name__)


class HealthServer:
    def __init__(self, *, app: FastAPI, port: int) -> None:
        self._app = app
        self._port = port
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        config = uvicorn.Config(app=self._app, host="0.0.0.0", port=self._port, log_level="warning")
        self._server = uvicorn.Server(config=config)
        self._task = asyncio.create_task(self._server.serve())

        _logger.info("Health server started on 0.0.0.0:%d", self._port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True

        if self._task is not None:
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._server = None
        self._task = None

        _logger.info("Health server stopped")
