from importlib.metadata import version

from libs.common.enums import ServiceNameEnum
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum
from libs.sentry_ext import setup_sentry
from libs.sqlmodel_ext import Session
from libs.taskiq_ext.liveness_check import start_heartbeat_loop, stop_heartbeat_loop
from libs.taskiq_ext.middlewares import TaskLifecycleLogMiddleware, TimeLimitMiddleware
from taskiq import SmartRetryMiddleware, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.brokers.shared_broker import async_shared_broker
from taskiq.middlewares.prometheus_middleware import PrometheusMiddleware
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from wearables.settings import settings
from wearables.utils import init_sqlmodel_engine

broker = RedisStreamBroker(url=settings.taskiq_redis_url).with_result_backend(
    result_backend=RedisAsyncResultBackend(
        redis_url=settings.taskiq_redis_url, result_ex_time=7 * 60 * 60 * 24
    )  # 1 week
)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

broker.add_middlewares(
    PrometheusMiddleware(server_port=settings.taskiq_metrics_port),
    TimeLimitMiddleware(default_timeout_seconds=60),
    SmartRetryMiddleware(use_jitter=True),
    TaskLifecycleLogMiddleware(),
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_worker_startup(state: TaskiqState) -> None:
    setup_logging(settings=settings, service_name=ServiceNameEnum.WEARABLES, process_type=ProcessTypeEnum.TASKIQ)
    setup_sentry(settings=settings, release=version("wearables"))

    db_url = settings.postgres_pooler_db_url or settings.postgres_direct_db_url
    engine = init_sqlmodel_engine(db_url=db_url)
    Session.configure(bind=engine)
    state.sqlmodel_engine = engine

    async_shared_broker.default_broker(broker)

    start_heartbeat_loop()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_worker_shutdown(state: TaskiqState) -> None:
    await stop_heartbeat_loop()
    await state.sqlmodel_engine.dispose()
