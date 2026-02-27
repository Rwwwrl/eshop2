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

### Defining Messages

```python
from messaging_contracts.common import Event

class HelloWorldEvent(Event):
    message: str
```

Rules:
- All messages are frozen Pydantic DTOs (`extra="forbid"`)
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
broker = RabbitBroker(url=settings.faststream_rabbitmq_url)

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
    _logger.info("Received HelloWorldEvent: %s", body)
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

## Worker Setup

Full consumer services use `AsgiFastStream`:

```python
from faststream.rabbit import RabbitBroker
from faststream.rabbit.prometheus import RabbitPrometheusMiddleware

_registry = CollectorRegistry()

broker = RabbitBroker(
    url=settings.faststream_rabbitmq_url,
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
| `faststream_rabbitmq_url` | `str` | required | RabbitMQ AMQP connection URL |
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
from libs.faststream_ext.consts import MESSAGE_CLASS_HEADER
from libs.utils import get_class_full_path
from rabbitmq_topology.entities import HELLO_WORLD_QUEUE

async def test_handle_hello_world_event(test_broker: TestRabbitBroker) -> None:
    event = HelloWorldEvent(message="Hello from test!")
    headers = {MESSAGE_CLASS_HEADER: get_class_full_path(cls=HelloWorldEvent)}

    await test_broker.publish(message=event, queue=HELLO_WORLD_QUEUE.name, headers=headers)
    handle_hello_world_event.mock.assert_called_once()
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

Services map `RABBITMQ_URL` to `FASTSTREAM_RABBITMQ_URL` via explicit env entry:

```yaml
env:
  - name: FASTSTREAM_RABBITMQ_URL
    valueFrom:
      secretKeyRef:
        name: rabbitmq-auth
        key: RABBITMQ_URL
```

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
4. Add `faststream_rabbitmq_url` to `env.yaml`
5. Add `FASTSTREAM_RABBITMQ_URL` env entry mapped from `rabbitmq-auth` secret in k8s deployment
6. Create `messaging/__init__.py`, `messaging/main.py`, `messaging/handlers.py`
7. Copy broker + `AsgiFastStream` setup from an existing service (e.g., `hello_world`)
8. Define message types in `messaging_contracts/` (or reuse existing ones)
9. Add exchange + bindings in `rabbitmq_topology/entities.py`
10. Add k8s manifests: `base/messaging/deployment.yaml`, `kustomization.yaml`, plus environment overlays
11. Add `test_broker` fixture to service `tests/conftest.py`

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
| DLQ naming | `<queue-name>.dlq` (e.g., `hello-world.dlq`) |
| Consumer queue | `declare=False` — fail-fast if topology not applied |
| Type discrimination | `message_type_filter(MessageClass)` on every subscriber handler |
| Router pattern | `RabbitRouter()` in `handlers.py`, included via `broker.include_router(router)` |
| Worker command | `uvicorn <service>.messaging.main:app --host 0.0.0.0 --port 8001 --workers 1` |
| Worker deployment | `<service>-messaging` on port 8001 (HTTP uses 8000) |
| Scale strategy | Horizontal via k8s replicas, not uvicorn workers |
| Test broker | `TestRabbitBroker` — function-scoped, in-memory |
| RabbitMQ secret | Centralized `rabbitmq-auth` ExternalSecret, referenced via `secretKeyRef` |
