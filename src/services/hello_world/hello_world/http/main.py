from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from libs.common.enums import ServiceNameEnum
from libs.fastapi_ext.middlewares import (
    RequestIdMiddleware,
    RequestResponseLoggingMiddleware,
    UnhandledExceptionMiddleware,
)
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum
from libs.sentry_ext import setup_sentry

from hello_world.http.routes import router
from hello_world.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings=settings, service_name=ServiceNameEnum.HELLO_WORLD, process_type=ProcessTypeEnum.FASTAPI)
    setup_sentry(settings=settings, release=version("hello-world"))
    yield


app = FastAPI(
    title="Hello World Service",
    lifespan=lifespan,
)

app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(router=router)
