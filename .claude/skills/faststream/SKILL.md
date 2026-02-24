---
name: faststream
description: Guides FastStream async messaging integration in MyEshop. Use when adding pub/sub messaging to a service, creating event/command message types, setting up a messaging worker, writing subscriber handlers, publishing events, or configuring messaging middleware. Trigger phrases include "faststream", "messaging", "publish event", "subscriber", "redis streams", "message handler", "event-driven".
---

# FastStream

Async event-driven messaging layer using **Redis Streams** as broker. Publishers send events into named streams, subscribers consume from those streams via consumer groups. No request/reply.

FastStream workers run as **separate processes** from HTTP servers: own `messaging/` folder, own `main.py`, own k8s Deployment.

## Quick Reference

| Component | Location | Import |
|-----------|----------|--------|
| Message base classes | `libs/faststream_ext/schemas/dtos.py` | `from libs.faststream_ext import Event, AsyncCommand, BaseMessage` |
| `@streams` decorator | `libs/faststream_ext/decorators.py` | `from libs.faststream_ext import streams` |
| `publish()` helper | `libs/faststream_ext/utils.py` | `from libs.faststream_ext import publish` |
| `message_type_filter()` | `libs/faststream_ext/utils.py` | `from libs.faststream_ext import message_type_filter` |
| Settings mixin | `libs/faststream_ext/settings.py` | `from libs.faststream_ext.settings import FaststreamSettingsMixin` |
| RequestIdMiddleware | `libs/faststream_ext/middlewares.py` | `from libs.faststream_ext.middlewares import RequestIdMiddleware` |
| TimeLimitMiddleware | `libs/faststream_ext/middlewares.py` | `from libs.faststream_ext.middlewares import TimeLimitMiddleware` |
| Stream name constants | `messaging_contracts/consts.py` | `from messaging_contracts.consts import HELLO_WORLD_STREAM` |
| Event definitions | `messaging_contracts/events.py` | `from messaging_contracts.events import HelloWorldEvent` |

## File Structure

```
<service>/
    messaging/
        __init__.py
        main.py          # Broker config, AsgiFastStream app, lifespan
        handlers.py      # RedisRouter, subscribers, handler functions
    settings.py          # Mixes in FaststreamSettingsMixin
```

Shared contracts live in a dedicated package:

```
src/messaging_contracts/
    messaging_contracts/
        __init__.py
        consts.py        # Stream name constants (HELLO_WORLD_STREAM, etc.)
        events.py        # Event classes decorated with @streams(...)
    pyproject.toml       # myeshop-messaging-contracts
```

## Message Type System

Two semantic message types, both inherit from `BaseMessage` (frozen Pydantic DTO):

| Type | Streams | Use case |
|------|---------|----------|
| `Event` | 1 or more | Domain events broadcast to multiple consumers |
| `AsyncCommand` | Exactly 1 | Targeted commands sent to a specific consumer |

### Defining Messages (in messaging_contracts)

```python
from libs.faststream_ext import Event, streams
from messaging_contracts.consts import HELLO_WORLD_STREAM, WEARABLES_STREAM

@streams(HELLO_WORLD_STREAM, WEARABLES_STREAM)
class HelloWorldEvent(Event):
    message: str
```

Rules:
- All messages are frozen Pydantic DTOs (`extra="forbid"`)
- `@streams()` is mandatory — assigns stream names to the message class
- Events can target multiple streams; AsyncCommands must target exactly one
- Stream name constants live in `messaging_contracts/consts.py`

## Publishing

Use the `publish()` helper — never call `broker.publish()` directly:

```python
from libs.faststream_ext import publish
from messaging_contracts.events import HelloWorldEvent

event = HelloWorldEvent(message="Hello!")
await publish(broker=faststream_broker, message=event)
```

`publish()` automatically:
- Sets `x-message-class` header (fully-qualified class path) for subscriber type discrimination
- Propagates `X-Request-ID` from ContextVar if present
- Publishes to **all** streams declared on the message class

### Publisher-Only Services (e.g., api_gateway)

Services that only publish don't need `AsgiFastStream`. Minimal broker setup:

```python
# <service>/messaging/main.py
from faststream.redis import RedisBroker
broker = RedisBroker(url=settings.faststream_redis_url)

# <service>/http/main.py — connect/disconnect in FastAPI lifespan
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await faststream_broker.connect()
    yield
    await faststream_broker.stop()
```

## Subscribing (Handler Pattern)

```python
from faststream.middlewares import AckPolicy
from faststream.redis import RedisRouter, StreamSub
from libs.faststream_ext import message_type_filter
from messaging_contracts.consts import HELLO_WORLD_STREAM
from messaging_contracts.events import HelloWorldEvent

router = RedisRouter()

subscriber = router.subscriber(
    stream=StreamSub(HELLO_WORLD_STREAM, max_records=settings.faststream_max_records),
    ack_policy=AckPolicy.ACK,
)

@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    _logger.info("Received HelloWorldEvent: %s", body)
```

Rules:
- Create a `RedisRouter()` — gets included into broker in `main.py`
- `StreamSub` with `max_records` cap for backpressure
- `AckPolicy.ACK` — explicit acknowledgment
- `message_type_filter(EventClass)` checks `x-message-class` header for type discrimination
- Multiple handlers can share one subscriber (different event types on the same stream)

## Worker Setup (messaging/main.py)

Full subscriber services use `AsgiFastStream` — wraps FastStream in ASGI with health/metrics endpoints:

```python
from faststream import ContextRepo
from faststream.asgi import AsgiFastStream, make_ping_asgi
from faststream.redis import RedisBroker
from faststream.redis.prometheus import RedisPrometheusMiddleware
from libs.faststream_ext.middlewares import RequestIdMiddleware, TimeLimitMiddleware
from prometheus_client import CollectorRegistry, make_asgi_app

_registry = CollectorRegistry()

broker = RedisBroker(
    url=settings.faststream_redis_url,
    graceful_timeout=settings.faststream_graceful_timeout,
    middlewares=[RedisPrometheusMiddleware(registry=_registry), RequestIdMiddleware, TimeLimitMiddleware],
)
broker.include_router(router)

@asynccontextmanager
async def lifespan(context: ContextRepo) -> AsyncGenerator[None, None]:
    setup_logging(settings=settings, service_name=..., process_type=ProcessTypeEnum.FASTSTREAM)
    setup_sentry(settings=settings, release=version("<service>"))

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
```

Key details:
- `_registry = CollectorRegistry()` — isolated Prometheus registry per worker
- Middleware order: `RedisPrometheusMiddleware` first, then `RequestIdMiddleware`, then `TimeLimitMiddleware`
- Lifespan receives `ContextRepo` (not `FastAPI`)
- `/health` — broker Redis ping check
- `/metrics` — Prometheus metrics endpoint

## Middlewares

| Middleware | Source | Purpose |
|-----------|--------|---------|
| `RedisPrometheusMiddleware` | `faststream.redis.prometheus` | Prometheus metrics collection |
| `RequestIdMiddleware` | `libs/faststream_ext/middlewares.py` | Propagates `X-Request-ID` from message headers into ContextVar |
| `TimeLimitMiddleware` | `libs/faststream_ext/middlewares.py` | Wraps handler in `asyncio.wait_for` (60s default) |

Both custom middlewares implement `consume_scope` (handler invocation level).

## Settings

Mix `FaststreamSettingsMixin` into the service settings:

```python
from libs.faststream_ext.settings import FaststreamSettingsMixin

class Settings(SentrySettingsMixin, PostgresSettingsMixin, FaststreamSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(_BASE_DIR / "env.yaml"), extra="ignore")
```

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `faststream_redis_url` | `str` | required | Redis connection URL |
| `faststream_max_records` | `int` | `100` | StreamSub prefetch cap (backpressure) |
| `faststream_graceful_timeout` | `float` | `65.0` | Broker wait for in-flight messages on shutdown |

## Testing

FastStream provides `TestRedisBroker` for in-memory testing — no real Redis needed.

```python
# conftest.py
from faststream.redis import TestRedisBroker
from <service>.messaging.main import broker as faststream_broker

@pytest_asyncio.fixture()
async def test_broker() -> AsyncGenerator[TestRedisBroker]:
    async with TestRedisBroker(faststream_broker) as br:
        yield br
```

### Handler Tests

```python
from libs.faststream_ext.utils import get_message_class_path
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER

async def test_handle_hello_world_event(test_broker: TestRedisBroker) -> None:
    event = HelloWorldEvent(message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_message_class_path(message_class=HelloWorldEvent)}

    await test_broker.publish(message=event, stream=HELLO_WORLD_STREAM, headers=headers)
    handle_hello_world_event.mock.assert_called_once()
```

Rules:
- Must manually add `MESSAGE_CLASS_HEADER` in tests (mirrors what `publish()` adds automatically)
- Handler gains `.mock` attribute inside `TestRedisBroker` context
- Use `get_message_class_path(message_class=EventClass)` for the header value

### Publisher Tests (HTTP routes)

```python
async def test_publish_event(async_client: AsyncClient, test_broker: TestRedisBroker) -> None:
    with patch.object(test_broker, "publish", wraps=test_broker.publish) as publish_spy:
        response = await async_client.post(url="/debug/publish-hello-world")

    assert publish_spy.call_count == 2  # event targets 2 streams
    published_streams = {call.kwargs["stream"] for call in publish_spy.call_args_list}
    assert published_streams == {HELLO_WORLD_STREAM, WEARABLES_STREAM}
```

## Adding FastStream to a New Service

1. Add dependencies: `poetry add 'faststream[redis,cli]'`
2. Add `myeshop-messaging-contracts` path dependency to service `pyproject.toml`
3. Mix `FaststreamSettingsMixin` into the service's `Settings` class
4. Add `faststream_redis_url` to `env.yaml` and k8s ConfigMaps
5. Create `messaging/__init__.py`, `messaging/main.py`, `messaging/handlers.py`
6. Copy broker + `AsgiFastStream` setup from an existing service (e.g., hello_world)
7. Define message types in `messaging_contracts/` (or reuse existing ones)
8. Add k8s manifests: `base/messaging/deployment.yaml`, `kustomization.yaml`, plus environment overlays
9. Add `test_broker` fixture to service `tests/conftest.py`

## Local Development

```bash
# justfile command
FASTSTREAM_CLI_RICH_MODE=none poetry run faststream run <service>.messaging.main:app
```

`FASTSTREAM_CLI_RICH_MODE=none` disables rich terminal output. In production, uvicorn runs the ASGI app directly.

See [references/k8s_deployment.md](references/k8s_deployment.md) for Kubernetes manifest patterns and graceful shutdown.

## Conventions

| Rule | Detail |
|------|--------|
| Message base class | Always inherit from `Event` or `AsyncCommand`, never `BaseMessage` directly |
| Stream decorator | `@streams(...)` is mandatory on every message class |
| Stream names | Centralized in `messaging_contracts/consts.py` |
| Publishing | Always use `publish(broker, message)` helper, never `broker.publish()` directly |
| Type discrimination | `message_type_filter(EventClass)` on every subscriber handler |
| Router pattern | `RedisRouter()` in `handlers.py`, included via `broker.include_router(router)` |
| Worker command | `uvicorn <service>.messaging.main:app --host 0.0.0.0 --port 8001 --workers 1` |
| Worker deployment name | `<service>-messaging` |
| Worker port | 8001 (HTTP uses 8000) |
| Scale strategy | Horizontal via k8s replicas, not uvicorn workers |
| Test broker | `TestRedisBroker` — function-scoped, in-memory |
