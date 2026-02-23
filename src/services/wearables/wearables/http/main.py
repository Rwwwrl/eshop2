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
from libs.sentry_ext import setup_sentry
from libs.settings import is_data_sensitive_env
from libs.sqlmodel_ext import Session
from taskiq.brokers.shared_broker import async_shared_broker

from wearables.background_tasks.main import broker
from wearables.http.routes import router
from wearables.messaging.main import broker as faststream_broker
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

    await faststream_broker.connect()

    yield

    await faststream_broker.close()
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

app.include_router(router=router)

setup_fastapi_prometheus(app=app)
