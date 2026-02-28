from importlib.metadata import version

from fastapi import FastAPI
from fastapi.responses import Response
from libs.common.enums import ServiceNameEnum
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum
from libs.rabbitmq_ext.utils import health_check as rabbitmq_health_check
from libs.sentry_ext import setup_sentry
from libs.sqlmodel_ext import Session
from libs.sqlmodel_ext.utils import health_check as sqlmodel_health_check
from libs.taskiq_ext.health_server import HealthServer
from libs.taskiq_ext.middlewares import (
    RequestIdMiddleware,
    SmartRetryWithBlacklistMiddleware,
    TaskLifecycleLogMiddleware,
    TimeLimitMiddleware,
)
from taskiq import TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.brokers.shared_broker import async_shared_broker
from taskiq.middlewares.prometheus_middleware import PrometheusMiddleware
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_aio_pika import AioPikaBroker

from wearables.settings import settings
from wearables.utils import init_sqlmodel_engine

broker = AioPikaBroker(
    url=settings.rabbitmq_url,
    exchange_name="taskiq-wearables",
    queue_name="taskiq-wearables",
    declare_exchange_kwargs={"durable": True},
    declare_queues_kwargs={"durable": True},
)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(async_shared_broker)],
)

broker.add_middlewares(
    RequestIdMiddleware(),
    PrometheusMiddleware(server_port=settings.taskiq_metrics_port),
    TimeLimitMiddleware(default_timeout_seconds=60),
    SmartRetryWithBlacklistMiddleware(use_jitter=True),
    TaskLifecycleLogMiddleware(),
)

health_app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
health_server = HealthServer(app=health_app, port=settings.taskiq_health_port)


@health_app.get("/health-check", status_code=204)
async def _health_check() -> Response:
    return Response(status_code=204)


@health_app.get("/readiness-check", status_code=204)
async def _readiness_check() -> Response:
    try:
        await rabbitmq_health_check(rabbitmq_url=settings.rabbitmq_url)
        await sqlmodel_health_check()
    except Exception:
        return Response(status_code=503)
    return Response(status_code=204)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_worker_startup(state: TaskiqState) -> None:
    setup_logging(settings=settings, service_name=ServiceNameEnum.WEARABLES, process_type=ProcessTypeEnum.TASKIQ)
    setup_sentry(settings=settings, release=version("wearables"))

    db_url = settings.postgres_pooler_db_url or settings.postgres_direct_db_url
    engine = init_sqlmodel_engine(db_url=db_url)
    Session.configure(bind=engine)
    state.sqlmodel_engine = engine

    async_shared_broker.default_broker(broker)

    await health_server.start()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_worker_shutdown(state: TaskiqState) -> None:
    await health_server.stop()
    await state.sqlmodel_engine.dispose()
