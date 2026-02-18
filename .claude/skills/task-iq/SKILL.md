---
name: task-iq
description: Guides TaskIQ async task queue integration in MyEshop. Use when adding background tasks to a service, setting up a messaging worker, writing task handlers, or configuring broker middleware. Trigger phrases include "taskiq", "task queue", "background task", "worker", "messaging handler", "broker", "kiq".
---

# TaskIQ

Async task queue (like Celery, but async-native). Uses Redis Streams as broker and Redis as result backend.

## Quick Reference

| Component | Location | Import |
|-----------|----------|--------|
| Broker setup | `<service>/messaging/main.py` | — |
| Task handlers | `<service>/messaging/handlers.py` | `from taskiq.brokers.shared_broker import async_shared_broker` |
| Settings mixin | `libs/taskiq_ext/settings.py` | `from libs.taskiq_ext import TaskiqSettingsMixin` |
| TimeLimitMiddleware | `libs/taskiq_ext/middlewares.py` | `from libs.taskiq_ext.middlewares import TimeLimitMiddleware` |
| Heartbeat loop | `libs/taskiq_ext/liveness_check.py` | `from libs.taskiq_ext.liveness_check import start_heartbeat_loop, stop_heartbeat_loop` |
| Redis health check | `libs/redis_ext/utils.py` | `from libs.redis_ext.utils import health_check as redis_health_check` |

## File Structure

```
<service>/
    messaging/
        __init__.py
        main.py          # Broker config, worker lifecycle
        handlers.py      # Task functions (@async_shared_broker.task)
    settings.py          # Mixes in TaskiqSettingsMixin
```

## Architecture

- Worker runs as a **separate process** — same Docker image, different k8s Deployment
- One worker process per pod (`--workers 1`), scale horizontally with k8s replicas
- `messaging/main.py` configures the real Redis broker and worker lifecycle
- `messaging/handlers.py` defines tasks via `@async_shared_broker.task()` — decoupled from concrete broker
- HTTP routes enqueue tasks by importing handlers and calling `.kiq()`
- `async_shared_broker.default_broker(broker)` wires the real broker at worker startup

## Broker Setup (messaging/main.py)

```python
from taskiq import SmartRetryMiddleware, TaskiqEvents, TaskiqState
from taskiq.brokers.shared_broker import async_shared_broker
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from libs.taskiq_ext.liveness_check import start_heartbeat_loop, stop_heartbeat_loop
from libs.taskiq_ext.middlewares import TimeLimitMiddleware

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

    async_shared_broker.default_broker(broker)
    start_heartbeat_loop()


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def _on_worker_shutdown(state: TaskiqState) -> None:
    await stop_heartbeat_loop()
    await state.sqlmodel_engine.dispose()
```

## Task Handler Pattern (messaging/handlers.py)

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

## Enqueuing from HTTP Routes

```python
from wearables.messaging.handlers import hello_world_task

@router.post("/debug/kiq-hello-world", status_code=status.HTTP_202_ACCEPTED)
async def kiq_hello_world() -> dict[str, str]:
    result = await hello_world_task.kiq()
    return {"task_id": result.task_id}
```

## Settings

Mix `TaskiqSettingsMixin` into the service settings:

```python
from libs.taskiq_ext import TaskiqSettingsMixin

class Settings(SentrySettingsMixin, PostgresSettingsMixin, TaskiqSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(_BASE_DIR / "env.yaml"), extra="ignore")
```

Adds `taskiq_redis_url: str` to the settings.

## Adding TaskIQ to a New Service

1. Add dependencies: `poetry add taskiq taskiq-redis`
2. Mix `TaskiqSettingsMixin` into the service's `Settings` class
3. Add `taskiq_redis_url` to `env.yaml` and k8s ConfigMaps
4. Create `messaging/__init__.py`, `messaging/main.py`, `messaging/handlers.py`
5. Copy broker setup pattern from wearables — adjust service name in logging/sentry calls
6. Add k8s manifests: `base/messaging/deployment.yaml` + `kustomization.yaml`, plus environment overlays
7. Set `run_messaging_deployment: true` in CI/CD workflow call
8. Add `taskiq_broker` fixture to service `tests/conftest.py`
9. Add Redis health check to HTTP `/readiness_check` endpoint

## Readiness Check

The HTTP readiness endpoint must verify Redis alongside Postgres:

```python
@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    await postgres_health_check()
    await redis_health_check(redis_url=settings.taskiq_redis_url)
    return {"status": "ok"}
```

## Middlewares

| Middleware | Source | Purpose |
|-----------|--------|---------|
| `TimeLimitMiddleware` | `libs/taskiq_ext/middlewares.py` | Sets default `timeout` label (60s) on tasks without one |
| `SmartRetryMiddleware` | `taskiq` (built-in) | Exponential backoff with jitter for retries |

## Testing

Use `InMemoryBroker` in tests — no Redis needed. Register via `async_shared_broker.default_broker(test_broker)`.

- Session-scoped `taskiq_broker` fixture in service `tests/conftest.py` — creates `InMemoryBroker`, calls startup/shutdown
- `fastapi_app` fixture must depend on `taskiq_broker`
- Handler tests: call `.kiq()` then `.wait_result()` to verify execution
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
- No `preStop` hook needed for messaging workers (they pull from Redis, no ingress traffic to drain)
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
| Worker command | `taskiq worker --workers 1 --max-async-tasks 4 --wait-tasks-timeout 65 --shutdown-timeout 10 <service>.messaging.main:broker <service>.messaging.handlers` |
| Deployment name | `<service>-messaging` |
| Liveness probe | Heartbeat file at `/tmp/taskiq_heartbeat` |
| Test broker | `InMemoryBroker` via `async_shared_broker.default_broker()` |
