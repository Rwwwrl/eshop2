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
from libs.prometheus_ext import setup_fastapi_prometheus
from libs.rabbitmq_ext.utils import health_check as rabbitmq_health_check
from libs.sentry_ext import setup_sentry
from libs.settings import is_data_sensitive_env
from libs.sqlmodel_ext import Session
from libs.sqlmodel_ext.utils import health_check as postgres_health_check
from taskiq.brokers.shared_broker import async_shared_broker

from wearables.background_tasks.main import broker
from wearables.http.v1 import v1_router
from wearables.settings import settings
from wearables.utils import init_sqlmodel_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging(settings=settings, service_name=ServiceNameEnum.WEARABLES, process_type=ProcessTypeEnum.FASTAPI)
    setup_sentry(settings=settings, release=version("wearables"))

    db_url = settings.postgres_pooler_db_url or settings.postgres_direct_db_url
    engine = init_sqlmodel_engine(db_url=db_url)
    Session.configure(bind=engine)
    app.state.sqlmodel_engine = engine

    await broker.startup()
    async_shared_broker.default_broker(broker)

    yield

    await broker.shutdown()
    await engine.dispose()


_is_sensitive = is_data_sensitive_env(environment=settings.environment)

app = FastAPI(
    title="Wearables Service",
    version=version("wearables"),
    description="Wearable data webhook ingestion service.",
    lifespan=lifespan,
    docs_url=None if _is_sensitive else "/docs",
    redoc_url=None if _is_sensitive else "/redoc",
    openapi_url=None if _is_sensitive else "/openapi.json",
)

app.add_middleware(RequestBodyLimitMiddleware, max_body_size=1_048_576)
app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    await postgres_health_check()
    await rabbitmq_health_check(rabbitmq_url=settings.rabbitmq_url)
    return {"status": "ok"}


app.include_router(router=v1_router, prefix="/v1")

setup_fastapi_prometheus(app=app)
