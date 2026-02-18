import os
from importlib.metadata import version

from libs.common.enums import ServiceNameEnum
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum
from libs.sentry_ext import setup_sentry
from libs.sqlmodel_ext import Session
from libs.taskiq_ext.liveness_check import start_heartbeat_loop, stop_heartbeat_loop
from libs.taskiq_ext.middlewares import TimeLimitMiddleware
from taskiq import InMemoryBroker, SmartRetryMiddleware, TaskiqEvents, TaskiqState
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from wearables.settings import settings
from wearables.utils import init_sqlmodel_engine

# NOTE @sosov: pytest sets PYTEST_VERSION env var on startup — use InMemoryBroker to avoid Redis dependency in tests.
if os.environ.get("PYTEST_VERSION"):
    broker = InMemoryBroker()
else:
    broker = RedisStreamBroker(url=settings.taskiq_redis_url).with_result_backend(
        result_backend=RedisAsyncResultBackend(redis_url=settings.taskiq_redis_url)
    )

broker.add_middlewares(
    TimeLimitMiddleware(default_timeout_seconds=60),
    SmartRetryMiddleware(use_jitter=True),
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def _on_worker_startup(state: TaskiqState) -> None:
    setup_logging(settings=settings, service_name=ServiceNameEnum.WEARABLES, process_type=ProcessTypeEnum.TASKIQ)
    setup_sentry(settings=settings, release=version("wearables"))

    db_url = settings.postgres_pooler_db_url or settings.postgres_direct_db_url
    engine = init_sqlmodel_engine(db_url=db_url)
    Session.configure(bind=engine)
    state.sqlmodel_engine = engine

    start_heartbeat_loop()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_worker_shutdown(state: TaskiqState) -> None:
    await stop_heartbeat_loop()
    await state.sqlmodel_engine.dispose()
