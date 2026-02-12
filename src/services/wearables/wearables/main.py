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
from libs.sqlmodel_ext import Session

from wearables.routes import router
from wearables.settings import settings
from wearables.utils import init_sqlmodel_engine

setup_logging(settings=settings, service_name=ServiceNameEnum.WEARABLES, process_type=ProcessTypeEnum.FASTAPI)

setup_sentry(settings=settings, release=version("wearables"))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    engine = init_sqlmodel_engine(db_url=settings.postgres_db_url)
    Session.configure(bind=engine)
    app.state.sqlmodel_engine = engine

    yield

    await engine.dispose()


app = FastAPI(
    title="Wearables Service",
    version=version("wearables"),
    description="Wearable data webhook ingestion service.",
    lifespan=lifespan,
)

app.add_middleware(RequestBodyLimitMiddleware, max_body_size=1_048_576)
app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.include_router(router=router)
