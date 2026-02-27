from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from importlib.metadata import version

from faststream import ContextRepo
from faststream.asgi import AsgiFastStream, make_ping_asgi
from faststream.rabbit import RabbitBroker
from faststream.rabbit.prometheus import RabbitPrometheusMiddleware
from libs.common.enums import ServiceNameEnum
from libs.faststream_ext.middlewares import RequestIdMiddleware, TimeLimitMiddleware
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum
from libs.sentry_ext import setup_sentry
from libs.sqlmodel_ext import Session
from prometheus_client import CollectorRegistry, make_asgi_app

from wearables.messaging.handlers import router
from wearables.settings import settings
from wearables.utils import init_sqlmodel_engine

_registry = CollectorRegistry()

broker = RabbitBroker(
    url=settings.faststream_rabbitmq_url,
    graceful_timeout=settings.faststream_graceful_timeout,
    middlewares=[RabbitPrometheusMiddleware(registry=_registry), RequestIdMiddleware, TimeLimitMiddleware],
)
broker.include_router(router)


@asynccontextmanager
async def lifespan(context: ContextRepo) -> AsyncGenerator[None, None]:
    setup_logging(settings=settings, service_name=ServiceNameEnum.WEARABLES, process_type=ProcessTypeEnum.FASTSTREAM)
    setup_sentry(settings=settings, release=version("wearables"))

    db_url = settings.postgres_pooler_db_url or settings.postgres_direct_db_url
    engine = init_sqlmodel_engine(db_url=db_url)
    Session.configure(bind=engine)

    yield

    await engine.dispose()


app = AsgiFastStream(
    broker,
    lifespan=lifespan,
    asgi_routes=[
        ("/health", make_ping_asgi(broker, timeout=5.0)),
        ("/metrics", make_asgi_app(_registry)),
    ],
)
