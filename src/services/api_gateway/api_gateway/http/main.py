from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI
from libs.common.enums import ServiceNameEnum
from libs.fastapi_ext.middlewares import (
    RequestBodyLimitMiddleware,
    RequestIdMiddleware,
    RequestResponseLoggingMiddleware,
    SecurityHeadersMiddleware,
    UnhandledExceptionMiddleware,
)
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum
from libs.sentry_ext import setup_sentry

from api_gateway.http.routes import router
from api_gateway.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings=settings, service_name=ServiceNameEnum.API_GATEWAY, process_type=ProcessTypeEnum.FASTAPI)
    setup_sentry(settings=settings, release=version("api-gateway"))
    yield


app = FastAPI(
    title="API Gateway",
    version=version("api-gateway"),
    description="Public-facing API Gateway for the e-shop platform.",
    lifespan=lifespan,
)

app.add_middleware(RequestBodyLimitMiddleware, max_body_size=1_048_576)
app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

app.include_router(router=router)
