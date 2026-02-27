---
name: task-iq
description: Guides TaskIQ async task queue integration in MyEshop. Use when adding background tasks to a service, setting up a background tasks worker, writing task definitions, or configuring broker middleware. Trigger phrases include "taskiq", "task queue", "background task", "worker", "background tasks", "broker", "kiq".
---

# TaskIQ

Async task queue (like Celery, but async-native). Uses RabbitMQ as broker via `taskiq-aio-pika` (fire-and-forget, no result backend).

## Quick Reference

| Component | Location | Import |
|-----------|----------|--------|
| Broker setup | `<service>/background_tasks/main.py` | — |
| Task definitions | `<service>/background_tasks/tasks.py` | `from taskiq.brokers.shared_broker import async_shared_broker` |
| Settings mixin | `libs/taskiq_ext/settings.py` | `from libs.taskiq_ext import TaskiqSettingsMixin` |
| RequestIdMiddleware | `libs/taskiq_ext/middlewares.py` | `from libs.taskiq_ext.middlewares import RequestIdMiddleware` |
| TimeLimitMiddleware | `libs/taskiq_ext/middlewares.py` | `from libs.taskiq_ext.middlewares import TimeLimitMiddleware` |
| Heartbeat loop | `libs/taskiq_ext/liveness_check.py` | `from libs.taskiq_ext.liveness_check import start_heartbeat_loop, stop_heartbeat_loop` |
| RabbitMQ health check | `libs/rabbitmq_ext/utils.py` | `from libs.rabbitmq_ext.utils import health_check as rabbitmq_health_check` |

## File Structure

```
<service>/
    background_tasks/
        __init__.py
        main.py          # Broker config, worker lifecycle
        tasks.py         # Task functions (@async_shared_broker.task)
    settings.py          # Mixes in TaskiqSettingsMixin
```

## Architecture

- Worker runs as a **separate process** — same Docker image, different k8s Deployment
- Scheduler runs as a **third process** — dispatches scheduled tasks to the broker on cron/interval
- One worker process per pod (`--workers 1`), scale horizontally with k8s replicas
- Exactly **one scheduler replica** — multiple replicas = duplicate task dispatches
- `background_tasks/main.py` configures the real RabbitMQ broker, scheduler, and worker lifecycle
- `background_tasks/tasks.py` defines tasks via `@async_shared_broker.task()` — decoupled from concrete broker
- HTTP routes enqueue tasks by importing task functions and calling `.kiq()`
- `async_shared_broker.default_broker(broker)` wires the real broker at worker startup

## Broker & Scheduler Setup (background_tasks/main.py)

```python
from taskiq import SmartRetryMiddleware, TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.brokers.shared_broker import async_shared_broker
from taskiq.schedule_sources import LabelScheduleSource
from taskiq_aio_pika import AioPikaBroker

from libs.taskiq_ext.liveness_check import start_heartbeat_loop, stop_heartbeat_loop
from libs.taskiq_ext.middlewares import RequestIdMiddleware, TimeLimitMiddleware

broker = AioPikaBroker(
    url=settings.rabbitmq_url,
    exchange_name="taskiq-<service>",
    queue_name="taskiq-<service>",
)

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)

broker.add_middlewares(
    RequestIdMiddleware(),
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

    async_shared_broker.default_broker(broker)
    start_heartbeat_loop()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_worker_shutdown(state: TaskiqState) -> None:
    await stop_heartbeat_loop()
    await state.sqlmodel_engine.dispose()
```

## Task Definition Pattern (background_tasks/tasks.py)

```python
from typing import Annotated

from taskiq import Context, TaskiqDepends
from taskiq.brokers.shared_broker import async_shared_broker


@async_shared_broker.task(retry_on_error=True, max_retries=3)
async def hello_world_task(context: Annotated[Context, TaskiqDepends()]) -> str:
    retries = int(context.message.labels.get("_retries", 0))
    return "Hello from TaskIQ!"
```

Rules:
- Always use `async_shared_broker.task()`, never the concrete broker directly
- Use `Annotated[Context, TaskiqDepends()]` for task context injection
- Access retry count via `context.message.labels.get("_retries", 0)`

## Scheduled Tasks

Use `schedule=[...]` label on `@async_shared_broker.task()` — `LabelScheduleSource` reads these at scheduler startup.

```python
# Cron — runs every 5 minutes
@async_shared_broker.task(schedule=[{"cron": "*/5 * * * *"}])
async def periodic_job() -> str:
    return "done"

# Interval — runs every 30 seconds
@async_shared_broker.task(schedule=[{"interval": 30}])
async def heartbeat() -> str:
    return "alive"
```

Schedule dict keys: `cron` | `interval` | `time` (one-shot). Optional: `args`, `kwargs`, `cron_offset` (timezone).

Rules:
- The scheduler process must import task modules to read labels — pass them as CLI args
- `--skip-first-run` prevents burst of overdue tasks on deploy/restart
- Scheduler command: `taskiq scheduler <service>.background_tasks.main:scheduler <service>.background_tasks.tasks --skip-first-run`

## Bulk Dispatch Pattern

Use `asyncio.Semaphore` + `asyncio.TaskGroup` to dispatch many tasks efficiently. The semaphore caps concurrent Redis calls; TaskGroup cancels all remaining tasks if one fails (e.g., Redis down).

```python
@async_shared_broker.task(schedule=[{"cron": "*/5 * * * *"}])
async def dispatch_wearable_events() -> str:
    sem = asyncio.Semaphore(200)

    async def _kick() -> None:
        async with sem:
            await process_5_min_batch.kiq()

    async with asyncio.TaskGroup() as tg:
        for _ in range(1500):
            tg.create_task(_kick())

    return "Dispatched 1500 tasks"
```

Rules:
- Semaphore concurrency (~200) should roughly match RabbitMQ channel pool size
- TaskGroup over `asyncio.gather` — fail-fast cancellation on errors
- No built-in bulk dispatch API in TaskIQ — this is the standard asyncio pattern
- Scales from 1,500 to 30,000+ by changing the count; semaphore ensures backpressure

## Enqueuing from HTTP Routes

```python
from wearables.background_tasks.tasks import hello_world_task

@router.post("/debug/kiq-hello-world", status_code=status.HTTP_202_ACCEPTED)
async def kiq_hello_world() -> dict[str, str]:
    result = await hello_world_task.kiq()
    return {"task_id": result.task_id}
```

## Request ID Propagation

`RequestIdMiddleware` automatically propagates `request_id` from HTTP requests into TaskIQ worker tasks, enabling log correlation across processes.

**How it works:**

1. `pre_send` (HTTP process): reads `request_id_var` ContextVar, writes to `message.labels["_request_id"]`
2. `pre_execute` (worker process): reads `_request_id` from labels, sets `request_id_var`
3. Logger formatters (`GKEJsonFormatter`, `DevFormatter`) already read from `request_id_var` — no task code changes needed

```python
# Registration in background_tasks/main.py — must be first middleware
broker.add_middlewares(
    RequestIdMiddleware(),
    PrometheusMiddleware(server_port=settings.taskiq_metrics_port),
    TimeLimitMiddleware(default_timeout_seconds=60),
    SmartRetryMiddleware(use_jitter=True),
    TaskLifecycleLogMiddleware(),
)
```

Rules:
- Label key is `_request_id` (underscore prefix = internal infrastructure, not for task authors)
- Both `pre_send` and `pre_execute` guard with `if request_id is not None` — tasks dispatched without HTTP context (scheduler, CLI) don't touch the ContextVar
- No `post_execute` cleanup needed — each task runs in its own async context, ContextVar is naturally scoped
- Task authors just use `logger.info(...)` — the request_id appears automatically in logs

## Settings

Mix `TaskiqSettingsMixin` into the service settings:

```python
from libs.taskiq_ext import TaskiqSettingsMixin

class Settings(SentrySettingsMixin, PostgresSettingsMixin, TaskiqSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(_BASE_DIR / "env.yaml"), extra="ignore")
```

Adds `rabbitmq_url: str` to the settings (shared with FastStream).

## Adding TaskIQ to a New Service

1. Add dependencies: `poetry add taskiq taskiq-aio-pika`
2. Mix `TaskiqSettingsMixin` into the service's `Settings` class
3. Add `rabbitmq_url` to `env.yaml` (shared with FastStream if also used)
4. Create `background_tasks/__init__.py`, `background_tasks/main.py`, `background_tasks/tasks.py`
5. Copy broker setup pattern from wearables — adjust service name in logging/sentry calls
6. Add k8s manifests: `base/background-tasks/workers-deployment.yaml`, `scheduler-deployment.yaml`, `kustomization.yaml`, plus environment overlays
7. Set `run_background_tasks_deployment: true` in CI/CD workflow call
   - CI waits for both `<service>-background-tasks` and `<service>-scheduler` rollouts
8. Add `taskiq_broker` fixture to service `tests/conftest.py`
9. Add RabbitMQ health check to HTTP `/readiness_check` endpoint

## Readiness Check

The HTTP readiness endpoint must verify RabbitMQ alongside Postgres:

```python
@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    await postgres_health_check()
    await rabbitmq_health_check(rabbitmq_url=settings.rabbitmq_url)
    return {"status": "ok"}
```

## Middlewares

| Middleware | Source | Purpose |
|-----------|--------|---------|
| `RequestIdMiddleware` | `libs/taskiq_ext/middlewares.py` | Propagates `request_id` from HTTP context into worker tasks via labels |
| `TimeLimitMiddleware` | `libs/taskiq_ext/middlewares.py` | Sets default `timeout` label (60s) on tasks without one |
| `SmartRetryMiddleware` | `taskiq` (built-in) | Exponential backoff with jitter for retries |

`RequestIdMiddleware` must be registered **first** — before other middlewares that might log.

## Testing

Use `InMemoryBroker` in tests — no Redis needed. Register via `async_shared_broker.default_broker(test_broker)`.

- Session-scoped `taskiq_broker` fixture in service `tests/conftest.py` — creates `InMemoryBroker`, calls startup/shutdown
- `fastapi_app` fixture must depend on `taskiq_broker`
- Task tests: call `.kiq()` then `.wait_result()` to verify execution
- Middleware tests: plain sync unit tests, no broker needed

See the testing skill for broader test patterns and conftest templates.

See [references/k8s_deployment.md](references/k8s_deployment.md) for Kubernetes manifest patterns and liveness probe setup.

## Graceful Shutdown

TaskIQ shutdown has **two sequential phases** after receiving SIGTERM:

1. **Task drain** (`--wait-tasks-timeout`): prefetcher stops, runner waits for in-flight tasks
2. **Broker cleanup** (`--shutdown-timeout`): event handlers, middleware shutdown, Redis close

```
SIGTERM → prefetcher stops → runner drains tasks (phase 1) → broker.shutdown() (phase 2) → exit
```

Configuration must align with `TimeLimitMiddleware` timeout and k8s `terminationGracePeriodSeconds`:

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| `TimeLimitMiddleware` | 60s | Max single task duration |
| `--wait-tasks-timeout` | 65s | Task limit + 5s buffer |
| `--shutdown-timeout` | 10s | Broker cleanup (engine dispose, Redis close) |
| `terminationGracePeriodSeconds` | 80s | 65 + 10 + 5s buffer before SIGKILL |

Rules:
- Always set `--wait-tasks-timeout` explicitly — default `None` waits forever, risks SIGKILL
- `terminationGracePeriodSeconds` must be > `wait-tasks-timeout` + `shutdown-timeout`
- No `preStop` hook needed for background task workers (they pull from RabbitMQ, no ingress traffic to drain)
- K8s sends exactly one SIGTERM, then one SIGKILL when grace period expires — no retries

See [references/k8s_deployment.md](references/k8s_deployment.md) for the full deployment manifest and shutdown details.

## Conventions

| Rule | Detail |
|------|--------|
| Broker import | Always `from taskiq.brokers.shared_broker import async_shared_broker` |
| Task decorator | `@async_shared_broker.task()`, never the concrete broker |
| Context injection | `context: Annotated[Context, TaskiqDepends()]` |
| Retry count access | `context.message.labels.get("_retries", 0)` |
| Enqueue method | `.kiq()` returns awaitable with `.task_id` |
| Worker command | `taskiq worker --workers 1 --max-async-tasks 4 --wait-tasks-timeout 65 --shutdown-timeout 10 <service>.background_tasks.main:broker <service>.background_tasks.tasks` |
| Scheduler command | `taskiq scheduler <service>.background_tasks.main:scheduler <service>.background_tasks.tasks --skip-first-run` |
| Worker deployment name | `<service>-background-tasks` |
| Scheduler deployment name | `<service>-scheduler` |
| Worker liveness probe | Heartbeat file at `/tmp/taskiq_heartbeat` |
| Scheduler replicas | Exactly 1 (multiple = duplicate dispatches) |
| Test broker | `InMemoryBroker` via `async_shared_broker.default_broker()` |
