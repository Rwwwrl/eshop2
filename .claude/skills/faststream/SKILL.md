---
name: faststream
description: Guides FastStream async messaging integration in MyEshop. Use when adding pub/sub messaging to a service, creating event/command message types, setting up a messaging worker, writing subscriber handlers, publishing events, or configuring messaging middleware. Trigger phrases include "faststream", "messaging", "publish event", "subscriber", "rabbitmq", "message handler", "event-driven".
---

# FastStream

Async messaging layer using **RabbitMQ** with **fanout exchanges**. Publishers send to exchanges, RabbitMQ routes to queues via bindings, subscribers consume from queues. No request/reply.

Workers run as **separate processes** from HTTP servers: own `messaging/` folder, own `main.py`, own k8s Deployment.

## Architecture

Three layers with strict knowledge boundaries:

| Layer | Responsibility | Knows |
|---|---|---|
| **Topology** (k8s Job) | Declares exchanges, queues, bindings | Everything |
| **Publisher** | Sends message to exchange | Only the exchange (resolved via `rabbitmq_topology`) |
| **Consumer** | Reads from queue, dispatches by filter | Only the queue name |

### Dependency Graph

```
messaging_contracts  (depends only on pydantic)
    ^
rabbitmq_topology    (depends on: messaging_contracts, faststream[rabbit])
    ^
libs                 (depends on: rabbitmq_topology, messaging_contracts)
    ^
services             (depends on: libs, messaging_contracts, rabbitmq_topology)
```

## Quick Reference

| Component | Location | Import |
|-----------|----------|--------|
| `Event`, `AsyncCommand` | `messaging_contracts/common/base_messages.py` | `from messaging_contracts.common import Event, AsyncCommand` |
| `get_message_full_class_path()` | `messaging_contracts/utils.py` | `from messaging_contracts.utils import get_message_full_class_path` |
| `get_class_full_path()` | `libs/utils.py` | `from libs.utils import get_class_full_path` |
| `publish()` | `libs/faststream_ext/utils.py` | `from libs.faststream_ext import publish` |
| `message_type_filter()` | `libs/faststream_ext/utils.py` | `from libs.faststream_ext import message_type_filter` |
| `dlq()` | `libs/faststream_ext/decorators.py` | `from libs.faststream_ext.decorators import dlq` |
| `retry()` | `libs/faststream_ext/rabbitmq_ext/decorators.py` | `from libs.faststream_ext.rabbitmq_ext.decorators import retry` |
| `RETRY_ATTEMPT_HEADER` | `libs/faststream_ext/consts.py` | `from libs.faststream_ext.consts import RETRY_ATTEMPT_HEADER` |
| `publish_to_delayed_retry_queue()` | `rabbitmq_topology/services.py` | `from rabbitmq_topology.services import publish_to_delayed_retry_queue` |
| `get_delayed_retry_queue_name()` | `rabbitmq_topology/utils.py` | `from rabbitmq_topology.utils import get_delayed_retry_queue_name` |
| `ProcessedMessage` | `libs/faststream_ext/models.py` | `from libs.faststream_ext.models import ProcessedMessage` |
| `ProcessedMessageRepository` | `libs/faststream_ext/repositories.py` | `from libs.faststream_ext.repositories import ProcessedMessageRepository` |
| `DuplicateMessageError` | `libs/faststream_ext/exceptions.py` | `from libs.faststream_ext.exceptions import DuplicateMessageError` |
| `FaststreamSettingsMixin` | `libs/faststream_ext/settings.py` | `from libs.faststream_ext.settings import FaststreamSettingsMixin` |
| `RequestIdMiddleware` | `libs/faststream_ext/middlewares.py` | `from libs.faststream_ext.middlewares import RequestIdMiddleware` |
| `TimeLimitMiddleware` | `libs/faststream_ext/middlewares.py` | `from libs.faststream_ext.middlewares import TimeLimitMiddleware` |
| Topology entities | `rabbitmq_topology/entities.py` | `from rabbitmq_topology.entities import HELLO_WORLD_QUEUE, HELLO_WORLD_DLQ, HELLO_WORLD_EVENT_EXCHANGE` |
| `get_exchange_for_message()` | `rabbitmq_topology/services.py` | `from rabbitmq_topology.services import get_exchange_for_message` |
| Event definitions | `messaging_contracts/events.py` | `from messaging_contracts.events import HelloWorldEvent` |

## File Structure

```
src/messaging_contracts/         # Message definitions (no libs dependency)
    messaging_contracts/
        common/
            __init__.py          # Exports BaseMessage, Event, AsyncCommand
            base_messages.py     # Message base classes (frozen Pydantic DTOs)
        utils.py                 # get_message_full_class_path() — used for exchange naming
        events.py                # Event classes (e.g., HelloWorldEvent)
        hello_world/
            async_commands.py    # AsyncCommand classes

src/rabbitmq_topology/           # Exchange/queue/binding declarations + apply script
    rabbitmq_topology/
        entities.py              # EXCHANGES, QUEUES, DEAD_LETTER_QUEUES, BINDINGS
        schemas/
            __init__.py          # Exports RabbitBinding
            dtos.py              # RabbitBinding DTO
        services.py              # get_exchange_for_message()
        apply.py                 # Reads RABBITMQ_URL from env, declares all topology

src/libs/                        # publish(), message_type_filter(), settings, middlewares

src/services/<service>/
    messaging/
        __init__.py
        main.py                  # Broker config, AsgiFastStream app, lifespan
        handlers.py              # RabbitRouter, subscribers, handler functions
    settings.py                  # Mixes in FaststreamSettingsMixin
```

## Message Types

Two semantic types, both frozen Pydantic DTOs inheriting `BaseMessage`:

| Type | Use case |
|------|----------|
| `Event` | Broadcast to multiple consumers via fanout exchange |
| `AsyncCommand` | Targeted command sent to a specific consumer |

`BaseMessage` provides two fields inherited by all messages:
- `logical_id: UUID` — required, used for idempotency (unique per message)
- `created_at: datetime` — auto-set to `utc_now()`, no need to pass explicitly

### Defining Messages

```python
from messaging_contracts.common import Event

class HelloWorldEvent(Event):
    message: str

# Usage — logical_id is always required
event = HelloWorldEvent(logical_id=uuid4(), message="Hello!")
```

Rules:
- All messages are frozen Pydantic DTOs (`extra="forbid"`)
- Always pass `logical_id=uuid4()` when constructing messages
- No decorator needed — exchange routing is defined in `rabbitmq_topology/entities.py`
- Message classes live in `messaging_contracts/`

## Topology

One fanout exchange per message type. Exchange name = fully-qualified class path (e.g., `messaging_contracts.events.HelloWorldEvent`). One queue per consuming service.

```python
# rabbitmq_topology/entities.py
from faststream.rabbit import RabbitExchange, RabbitQueue
from faststream.rabbit.schemas import ExchangeType
from messaging_contracts.utils import get_message_full_class_path

HELLO_WORLD_EVENT_EXCHANGE = RabbitExchange(
    name=get_message_full_class_path(message_class=HelloWorldEvent),
    type=ExchangeType.FANOUT,
)

# DLQ queues — declared before main queues
HELLO_WORLD_DLQ = RabbitQueue(name="hello-world.dlq")
DEAD_LETTER_QUEUES: list[RabbitQueue] = [HELLO_WORLD_DLQ]

# Main queues — with DLX arguments pointing to DLQ
HELLO_WORLD_QUEUE = RabbitQueue(
    name="hello-world",
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": HELLO_WORLD_DLQ.name,
    },
)

BINDINGS: list[RabbitBinding] = [
    RabbitBinding(exchange=HELLO_WORLD_EVENT_EXCHANGE, queues=[HELLO_WORLD_QUEUE]),
]
```

Apply topology locally: `RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply`

All operations are **idempotent** — safe to run on every deploy.

**Migration note:** Adding `arguments` to existing queues requires deleting and recreating them in RabbitMQ (queue arguments are immutable). Delete via Management UI locally, or delete queues before deploying the topology Job in test-eu.

## Publishing

Always use the `publish()` helper — never call `broker.publish()` directly:

```python
from libs.faststream_ext import publish
from messaging_contracts.events import HelloWorldEvent

event = HelloWorldEvent(message="Hello!")
await publish(broker=faststream_broker, message=event)
```

`publish()` automatically:
- Looks up the exchange via `get_exchange_for_message()`
- Sets `x-message-class` header via `get_class_full_path(cls=type(message))`
- Propagates `X-Request-ID` from ContextVar
- Publishes once to the exchange — RabbitMQ handles fan-out to bound queues

### Publisher-Only Services (e.g., api_gateway)

No `AsgiFastStream` needed. Bare broker connected in FastAPI lifespan:

```python
# <service>/messaging/main.py
from faststream.rabbit import RabbitBroker
broker = RabbitBroker(url=settings.rabbitmq_url)

# <service>/http/main.py
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await faststream_broker.connect()
    yield
    await faststream_broker.stop()
```

## Subscribing

```python
from faststream import AckPolicy
from faststream.rabbit import RabbitQueue, RabbitRouter
from libs.faststream_ext import message_type_filter
from messaging_contracts.events import HelloWorldEvent
from rabbitmq_topology.entities import HELLO_WORLD_QUEUE

router = RabbitRouter()

_QUEUE = RabbitQueue(name=HELLO_WORLD_QUEUE.name, declare=False)

subscriber = router.subscriber(queue=_QUEUE, ack_policy=AckPolicy.ACK)

@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    async with Session() as session, session.begin():
        try:
            await ProcessedMessageRepository.save(session=session, logical_id=body.logical_id)
        except IntegrityError as exc:
            raise DuplicateMessageError from exc

        # Business logic here — runs inside the same transaction
```

Rules:
- `RabbitRouter()` in `handlers.py`, included via `broker.include_router(router)` in `main.py`
- Import queue name from `rabbitmq_topology.entities` — consumer only knows its queue
- `declare=False` — fail-fast if topology Job hasn't run
- `ack_policy=AckPolicy.ACK` — always ack (FastStream default is `REJECT_ON_ERROR`, we override)
- `message_type_filter(MessageClass)` checks `x-message-class` header for type discrimination
- Multiple handlers can share one subscriber (different message types on the same queue)
- `ack_policy` is per-subscriber, not per-handler — all handlers on one subscriber share the same policy
- **Zero knowledge of exchanges or bindings** in consumer code

## Idempotent Handlers

Every handler must be idempotent. The `ProcessedMessage` table (unique on `logical_id`) ensures each message is processed exactly once. The save happens inside the same DB transaction as the business logic — if business logic fails, the `ProcessedMessage` row is rolled back too.

### Handler Pattern

```python
from libs.faststream_ext.exceptions import DuplicateMessageError
from libs.faststream_ext.repositories import ProcessedMessageRepository
from libs.sqlmodel_ext import Session
from sqlalchemy.exc import IntegrityError

@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    async with Session() as session, session.begin():
        try:
            await ProcessedMessageRepository.save(session=session, logical_id=body.logical_id)
        except IntegrityError as exc:
            raise DuplicateMessageError from exc

        # Business logic here — runs inside the same transaction
```

Rules:
- `ProcessedMessageRepository.save()` **must** be the first operation inside the transaction
- `IntegrityError` (unique constraint violation) is chained into `DuplicateMessageError`
- `DuplicateMessageError` is passed through by `@retry()` — duplicates are never retried
- `ack_policy=AckPolicy.ACK` means duplicates are acked (no redelivery loop)

### Setup for New Services

1. Create an expand migration for `processed_message` table:
   ```bash
   cd src/services/<service>
   poetry run alembic -c alembic.ini revision --head expand@head -m "add processed_message table"
   ```
2. The migration creates the table defined by `libs.faststream_ext.models.ProcessedMessage` (id, logical_id with unique constraint, created_at, updated_at)
3. Add `ProcessedMessage` to `autocleared_sqlmodel_tables` in `tests/conftest.py`:
   ```python
   from libs.faststream_ext.models import ProcessedMessage

   @pytest.fixture(scope="session")
   def autocleared_sqlmodel_tables() -> list[type[BaseSqlModel]]:
       return [ProcessedMessage]  # add alongside other tables
   ```
4. Worker `main.py` must init the DB engine and bind `Session` in lifespan (see Worker Setup)

## Dead Letter Queue (DLQ)

Failed messages are routed to DLQ via RabbitMQ's native DLX mechanism. The `dlq` decorator catches exceptions in handlers and raises `NackMessage(requeue=False)`, which triggers DLX routing.

**How it works:**
1. Main queue has `x-dead-letter-exchange: ""` and `x-dead-letter-routing-key: <queue>.dlq` arguments
2. `ack_policy=AckPolicy.ACK` on subscriber — unhandled exceptions still ack (safe default, no message loops)
3. `@dlq()` decorator on handler — catches exceptions, raises `NackMessage(requeue=False)`
4. RabbitMQ sees nack without requeue → routes to DLX → lands in `<queue>.dlq`

### `dlq` decorator

```python
from libs.faststream_ext.decorators import dlq

@subscriber(filter=message_type_filter(HelloWorldEvent))
@dlq()  # catches all exceptions
async def handle_event(body: HelloWorldEvent) -> None:
    process(body)

@subscriber(filter=message_type_filter(SomeCommand))
@dlq(exceptions=(ValueError, TimeoutError))  # catches only specific exceptions
async def handle_command(body: SomeCommand) -> None:
    process(body)
```

Rules:
- `@dlq()` goes **between** `@subscriber(filter=...)` and the handler function
- Default `exceptions=(Exception,)` — catches all exceptions
- Uses `@functools.wraps` — preserves handler signature for FastStream's DI
- `NackMessage` is a `HandlerException` subclass — overrides `ack_policy` and is suppressed (not propagated)
- Without `@dlq()`, exceptions are acked (due to `AckPolicy.ACK`) and the message is lost

### Adding DLQ to a new queue

1. Add DLQ queue in `rabbitmq_topology/entities.py`: `MY_QUEUE_DLQ = RabbitQueue(name="my-queue.dlq")`
2. Add to `DEAD_LETTER_QUEUES` list
3. Add DLX arguments to the main queue:
   ```python
   MY_QUEUE = RabbitQueue(
       name="my-queue",
       arguments={
           "x-dead-letter-exchange": "",
           "x-dead-letter-routing-key": MY_QUEUE_DLQ.name,
       },
   )
   ```
4. `apply.py` declares `DEAD_LETTER_QUEUES` before `QUEUES` automatically
5. Add `@dlq()` to handlers that should route failures to DLQ

## Retry Decorator

Automatic retry with delayed re-delivery using RabbitMQ's TTL + DLX mechanism. Failed messages are republished to a `<queue>.delayed-retry` queue with a TTL; when the TTL expires, RabbitMQ routes them back to the original queue via DLX.

**How it works:**
1. Handler throws → `@retry()` catches the exception
2. If `retry_attempt <= max_attempts`: publishes a copy to the delayed-retry queue with `x-retry-attempt` header incremented and `expiration` set (countdown × 1000 ms)
3. Original exception is re-raised → FastStream applies `ack_policy` naturally (ACK → original message acked, retry copy waits in delayed-retry queue)
4. When TTL expires on the delayed-retry queue, RabbitMQ routes back to the original queue via DLX
5. If `retry_attempt > max_attempts` and `dlq=True`: raises `NackMessage(requeue=False)` → message goes to DLQ
6. If `retry_attempt > max_attempts` and `dlq=False`: re-raises the original exception

### `retry` decorator

```python
from libs.faststream_ext.rabbitmq_ext.decorators import retry

@subscriber(filter=message_type_filter(SomeEvent))
@retry(max_attempts=3, countdown=5, dlq=True)
async def handle_event(body: SomeEvent, context: ContextRepoDep) -> None:
    process(body)
```

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `max_attempts` | `int` | required | Maximum number of retry attempts before giving up |
| `countdown` | `int` | required | Delay in seconds before retried message is redelivered |
| `exceptions` | `tuple[type[Exception], ...]` | `(Exception,)` | Which exceptions trigger a retry |
| `dlq` | `bool` | `False` | If `True`, sends to DLQ after max attempts; if `False`, re-raises |

Rules:
- `@retry()` goes **between** `@subscriber(filter=...)` and the handler function
- Handler **must** accept `context: ContextRepoDep` — the decorator uses it to resolve `message`, `broker`, and `handler_`
- FastStream's `AckMessage`, `NackMessage`, `RejectMessage` are never intercepted — they pass through
- Uses `@functools.wraps` — preserves handler signature for FastStream's DI
- `countdown` is in **seconds** (converted to ms internally via `× 1000`)
- The `x-retry-attempt` header is incremented on each retry, starting from 0

### Delayed-Retry Queue Topology

Each queue that uses `@retry()` needs a corresponding delayed-retry queue in `rabbitmq_topology/entities.py`:

```python
# rabbitmq_topology/entities.py
HELLO_WORLD_DELAYED_RETRY = RabbitQueue(
    name=f"{HELLO_WORLD_QUEUE.name}.delayed-retry",
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": HELLO_WORLD_QUEUE.name,
    },
)

DELAYED_RETRY_QUEUES: list[RabbitQueue] = [
    HELLO_WORLD_DELAYED_RETRY,
    WEARABLES_DELAYED_RETRY,
]
```

The delayed-retry queue has DLX arguments pointing back to the original queue — when TTL expires, the message is routed back for reprocessing.

### Adding Retry to a New Queue

1. Add delayed-retry queue in `rabbitmq_topology/entities.py`:
   ```python
   MY_QUEUE_DELAYED_RETRY = RabbitQueue(
       name=f"{MY_QUEUE.name}.delayed-retry",
       arguments={
           "x-dead-letter-exchange": "",
           "x-dead-letter-routing-key": MY_QUEUE.name,
       },
   )
   ```
2. Add to `DELAYED_RETRY_QUEUES` list
3. Apply topology: `RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply`
4. Add `@retry(max_attempts=..., countdown=...)` to handlers
5. Add `context: ContextRepoDep` parameter to the handler function

### Retry vs DLQ

| Decorator | Purpose | After exhaustion |
|-----------|---------|------------------|
| `@dlq()` | Immediate DLQ on first failure | N/A — no retry |
| `@retry(dlq=False)` | Retry N times, then re-raise | Exception propagates, `ack_policy` decides |
| `@retry(dlq=True)` | Retry N times, then DLQ | `NackMessage(requeue=False)` → DLQ via DLX |

Use `@retry(dlq=True)` when you want both retry and DLQ. Don't stack `@dlq()` on top of `@retry()`.

## Worker Setup

Full consumer services use `AsgiFastStream`:

```python
from faststream.rabbit import RabbitBroker
from faststream.rabbit.prometheus import RabbitPrometheusMiddleware

_registry = CollectorRegistry()

broker = RabbitBroker(
    url=settings.rabbitmq_url,
    graceful_timeout=settings.faststream_graceful_timeout,
    middlewares=[RabbitPrometheusMiddleware(registry=_registry), RequestIdMiddleware, TimeLimitMiddleware],
)
broker.include_router(router)

app = AsgiFastStream(
    broker,
    lifespan=lifespan,
    asgi_routes=[
        ("/health", make_ping_asgi(broker, timeout=5.0)),
        ("/metrics", make_asgi_app(_registry)),
    ],
)
```

Middleware order: `RabbitPrometheusMiddleware` first, then `RequestIdMiddleware`, then `TimeLimitMiddleware`.

## Settings

Mix `FaststreamSettingsMixin` into the service settings:

```python
from libs.faststream_ext.settings import FaststreamSettingsMixin

class Settings(SentrySettingsMixin, FaststreamSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(_BASE_DIR / "env.yaml"), extra="ignore")
```

| Setting | Type | Default | Purpose |
|---------|------|---------|---------|
| `rabbitmq_url` | `str` | required | RabbitMQ AMQP connection URL |
| `faststream_graceful_timeout` | `float` | `65.0` | Broker wait for in-flight messages on shutdown |

## Testing

`TestRabbitBroker` provides in-memory testing — no real RabbitMQ needed.

### Fixture

```python
# conftest.py
from faststream.rabbit import TestRabbitBroker
from <service>.messaging.main import broker as faststream_broker

@pytest_asyncio.fixture(scope="function")
async def test_broker() -> AsyncGenerator[TestRabbitBroker]:
    async with TestRabbitBroker(faststream_broker) as br:
        yield br
```

### Handler Tests

```python
from uuid import uuid4
from unittest.mock import AsyncMock, patch

from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER
from libs.faststream_ext.exceptions import DuplicateMessageError
from libs.utils import get_class_full_path
from rabbitmq_topology.resources import HELLO_WORLD_QUEUE
from sqlalchemy.ext.asyncio import AsyncEngine

async def test_handle_hello_world_event(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    event = HelloWorldEvent(logical_id=uuid4(), message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    with patch("hello_world.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)

        handle_hello_world_event.mock.assert_called_once()
        mock_business.assert_called_once()
```

### Duplicate Rejection Tests

```python
async def test_handle_hello_world_event_when_duplicate_published(
    test_broker: TestRabbitBroker, sqlmodel_engine: AsyncEngine
) -> None:
    logical_id = uuid4()
    event = HelloWorldEvent(logical_id=logical_id, message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    with patch("hello_world.messaging.handlers.execute_business_logic", new_callable=AsyncMock) as mock_business:
        await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)

        with pytest.raises(DuplicateMessageError):
            await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)

        mock_business.assert_called_once()  # business logic ran only on first delivery
```

### Publisher Tests

```python
async def test_publish_event(async_client: AsyncClient, test_broker: TestRabbitBroker) -> None:
    with patch.object(test_broker, "publish", wraps=test_broker.publish) as publish_spy:
        response = await async_client.post(url="/debug/publish-hello-world")

    assert publish_spy.call_count == 1
    assert publish_spy.call_args_list[0].kwargs["exchange"] == HELLO_WORLD_EVENT_EXCHANGE
```

### Test Rules

- Publish to the **queue** in tests — `TestRabbitBroker` doesn't simulate exchange routing
- Must manually set `MESSAGE_CLASS_HEADER` (mirrors what `publish()` does automatically)
- Header value = `get_class_full_path(cls=MessageClass)`
- Queue name from topology: `HELLO_WORLD_QUEUE.name`, `WEARABLES_QUEUE.name`
- Handler gains `.mock` attribute inside `TestRabbitBroker` context
- Always pass `logical_id=uuid4()` when constructing messages in tests
- Handler tests require `sqlmodel_engine: AsyncEngine` fixture (DB needed for `ProcessedMessage`)
- Duplicate tests: publish same `logical_id` twice, assert `DuplicateMessageError` on second, assert business logic ran once

## Kubernetes

### RabbitMQ Secret (centralized)

```yaml
# deploy/k8s/infrastructure/external-secrets/test-eu/external-secrets/rabbitmq-auth.yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: rabbitmq-auth
spec:
  secretStoreRef:
    name: gcp-cluster-store
    kind: ClusterSecretStore
  target:
    name: rabbitmq-auth
  data:
    - secretKey: RABBITMQ_URL
      remoteRef:
        key: rabbitmq-url
```

Services use `envFrom: secretRef` to pick up `RABBITMQ_URL` automatically from their ExternalSecret.

### Topology Job

```yaml
command: ["poetry", "run", "python", "-m", "rabbitmq_topology.apply"]
envFrom:
  - secretRef:
      name: rabbitmq-auth
```

See [references/k8s_deployment.md](references/k8s_deployment.md) for deployment manifests and graceful shutdown.

## Step-by-Step Guides

### Adding FastStream to a New Service

1. Add dependencies: `poetry add 'faststream[rabbit,cli]'`
2. Add `myeshop-messaging-contracts`, `myeshop-rabbitmq-topology` path dependencies
3. Mix `FaststreamSettingsMixin` into the service `Settings` class
4. Add `rabbitmq_url` to `env.yaml`
5. Add `RABBITMQ_URL` to the service's ExternalSecret (mapped from `rabbitmq-url` GCP secret)
6. Create `messaging/__init__.py`, `messaging/main.py`, `messaging/handlers.py`
7. Copy broker + `AsgiFastStream` setup from an existing service (e.g., `hello_world`)
8. Define message types in `messaging_contracts/` (or reuse existing ones)
9. Add exchange + bindings in `rabbitmq_topology/entities.py`
10. Add k8s manifests: `base/messaging/deployment.yaml`, `kustomization.yaml`, plus environment overlays
11. Add `test_broker` fixture to service `tests/conftest.py`
12. Create `processed_message` expand migration: `poetry run alembic -c alembic.ini revision --head expand@head -m "add processed_message table"`
13. Add `ProcessedMessage` to `autocleared_sqlmodel_tables` in `tests/conftest.py`

### Adding a New Message Type

1. Define the message class in `messaging_contracts/` (inherit `Event` or `AsyncCommand`)
2. Add exchange in `rabbitmq_topology/entities.py` using `get_message_full_class_path()`
3. Add binding(s) to connect the exchange to consumer queue(s)
4. Run `RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply`
5. Add handler with `message_type_filter()` in the consumer service

## Local Development

```bash
# Start RabbitMQ
docker compose up -d rabbitmq

# Apply topology
RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply

# RabbitMQ management UI
open http://localhost:25672  # guest/guest

# Run worker
FASTSTREAM_CLI_RICH_MODE=none poetry run faststream run <service>.messaging.main:app
```

## Conventions

| Rule | Detail |
|------|--------|
| Message base class | Inherit `Event` or `AsyncCommand`, never `BaseMessage` directly |
| Exchange naming | Fully-qualified class path via `get_message_full_class_path()` |
| Exchange type | Always `FANOUT` |
| Topology management | Centralized in `rabbitmq_topology/entities.py`, applied by k8s Job |
| Publishing | Always `publish(broker, message)`, never `broker.publish()` directly |
| Ack policy | Always `ack_policy=AckPolicy.ACK` on subscriber (override FastStream default) |
| DLQ decorator | `@dlq()` on handlers that should route failures to DLQ |
| Retry decorator | `@retry(max_attempts=..., countdown=..., dlq=True)` for delayed retry with optional DLQ |
| Retry queue naming | `<queue-name>.delayed-retry` (e.g., `hello-world.delayed-retry`) |
| DLQ naming | `<queue-name>.dlq` (e.g., `hello-world.dlq`) |
| Consumer queue | `declare=False` — fail-fast if topology not applied |
| Type discrimination | `message_type_filter(MessageClass)` on every subscriber handler |
| Router pattern | `RabbitRouter()` in `handlers.py`, included via `broker.include_router(router)` |
| Worker command | `uvicorn <service>.messaging.main:app --host 0.0.0.0 --port 8001 --workers 1` |
| Worker deployment | `<service>-messaging` on port 8001 (HTTP uses 8000) |
| Scale strategy | Horizontal via k8s replicas, not uvicorn workers |
| Idempotent handlers | `ProcessedMessageRepository.save()` first in transaction, `IntegrityError` → `DuplicateMessageError` |
| Message `logical_id` | Always `logical_id=uuid4()` — required field on all messages |
| Test broker | `TestRabbitBroker` — function-scoped, in-memory |
| RabbitMQ secret | Centralized `rabbitmq-auth` ExternalSecret, referenced via `secretKeyRef` |
