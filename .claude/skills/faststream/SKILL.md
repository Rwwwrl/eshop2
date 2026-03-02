---
name: faststream
description: Guides FastStream async messaging integration in MyEshop. Use when adding pub/sub messaging to a service, creating event/command message types, setting up a messaging worker, writing subscriber handlers, publishing events, or configuring messaging middleware. Trigger phrases include "faststream", "messaging", "publish event", "subscriber", "rabbitmq", "message handler", "event-driven".
---

# FastStream

Async messaging layer using **RabbitMQ** with **fanout exchanges**. Publishers send to exchanges, RabbitMQ routes to queues via bindings, subscribers consume from queues. No request/reply.

Workers run as **separate processes** from HTTP servers: own `messaging/` folder, own `main.py`, own k8s Deployment.

## Architecture

Three layers with strict knowledge boundaries:

| Layer                  | Responsibility                         | Knows                                                |
| ---------------------- | -------------------------------------- | ---------------------------------------------------- |
| **Topology** (k8s Job) | Declares exchanges, queues, bindings   | Everything                                           |
| **Publisher**          | Sends message to exchange              | Only the exchange (resolved via `rabbitmq_topology`) |
| **Consumer**           | Reads from queue, dispatches by filter | Only the queue name                                  |

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

| Component                    | Location                                         | Import                                                                      |
| ---------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------- |
| `Event`, `AsyncCommand`      | `messaging_contracts/common/base_messages.py`    | `from messaging_contracts.common import Event, AsyncCommand`                |
| `get_exchange_name()`        | `messaging_contracts/common/base_messages.py`    | `from messaging_contracts.common import get_exchange_name`                  |
| `publish()`                  | `libs/faststream_ext/utils.py`                   | `from libs.faststream_ext import publish`                                   |
| `message_type_filter()`      | `libs/faststream_ext/utils.py`                   | `from libs.faststream_ext import message_type_filter`                       |
| `dlq()`                      | `libs/faststream_ext/decorators.py`              | `from libs.faststream_ext.decorators import dlq`                            |
| `retry()`                    | `libs/faststream_ext/rabbitmq_ext/decorators.py` | `from libs.faststream_ext.rabbitmq_ext.decorators import retry`             |
| `RETRY_ATTEMPT_HEADER`       | `libs/faststream_ext/consts.py`                  | `from libs.faststream_ext.consts import RETRY_ATTEMPT_HEADER`               |
| `ProcessedMessage`           | `libs/faststream_ext/models.py`                  | `from libs.faststream_ext.models import ProcessedMessage`                   |
| `ProcessedMessageRepository` | `libs/faststream_ext/repositories.py`            | `from libs.faststream_ext.repositories import ProcessedMessageRepository`   |
| `DuplicateMessageError`      | `libs/faststream_ext/exceptions.py`              | `from libs.faststream_ext.exceptions import DuplicateMessageError`          |
| `FaststreamSettingsMixin`    | `libs/faststream_ext/settings.py`                | `from libs.faststream_ext.settings import FaststreamSettingsMixin`          |
| `RequestIdMiddleware`        | `libs/faststream_ext/middlewares.py`             | `from libs.faststream_ext.middlewares import RequestIdMiddleware`           |
| `TimeLimitMiddleware`        | `libs/faststream_ext/middlewares.py`             | `from libs.faststream_ext.middlewares import TimeLimitMiddleware`           |
| Topology entities            | `rabbitmq_topology/resources.py`                  | `from rabbitmq_topology.resources import HELLO_WORLD_QUEUE, HELLO_WORLD_DLQ` |
| `get_exchange_for_message()` | `rabbitmq_topology/services.py`                  | `from rabbitmq_topology.services import get_exchange_for_message`           |
| Event definitions            | `messaging_contracts/v1/events.py`               | `from messaging_contracts.v1.events import HelloWorldEvent`                 |

## File Structure

```
src/messaging_contracts/         # Message definitions (no libs dependency)
    messaging_contracts/
        common/
            __init__.py          # Exports BaseMessage, Event, AsyncCommand
            base_messages.py     # Message base classes (frozen Pydantic DTOs, extra="allow")
        __init__.py              # Imports all message modules to trigger code uniqueness validation
        v1/
            __init__.py
            events.py            # Event classes (e.g., HelloWorldEvent)
            hello_world/
                async_commands.py # AsyncCommand classes

src/rabbitmq_topology/           # Exchange/queue/binding declarations + apply script
    rabbitmq_topology/
        entities.py              # EXCHANGES, QUEUES, DEAD_LETTER_QUEUES, BINDINGS
        schemas/dtos.py          # RabbitBinding DTO
        services.py              # get_exchange_for_message()
        apply.py                 # Reads RABBITMQ_URL from env, declares all topology

src/services/<service>/
    messaging/
        __init__.py
        main.py                  # Broker config, AsgiFastStream app, lifespan
        v1/
            __init__.py          # Exports v1_router
            handlers.py          # RabbitRouter, subscribers, handler functions
    settings.py                  # Mixes in FaststreamSettingsMixin
```

## Message Types

Two semantic types, both frozen Pydantic DTOs inheriting `BaseMessage`:

| Type           | Use case                                            |
| -------------- | --------------------------------------------------- |
| `Event`        | Broadcast to multiple consumers via fanout exchange |
| `AsyncCommand` | Targeted command sent to a specific consumer        |

`BaseMessage` provides:

- `code: ClassVar[int]` — stable numeric identifier, used for exchange naming and message filtering. Every concrete subclass must define a unique `code`. Enforced by `__init_subclass__` at import time.
- `persistent: ClassVar[bool]` — controls RabbitMQ `delivery_mode`. `True` = survives broker restart (written to disk), `False` = transient (memory only, better throughput). Every concrete subclass must define it. Enforced by `__init_subclass__` at import time.
- `logical_id: UUID` — required, used for idempotency (unique per message)
- `created_at: datetime` — auto-set to `utc_now()`
- `model_serializer` injects `code` into serialized body
- `model_validator` strips `code` from input (prevents `code` leaking into extras)

### Defining Messages

```python
from typing import ClassVar
from messaging_contracts.common import Event

class HelloWorldEvent(Event):
    code: ClassVar[int] = 1
    persistent: ClassVar[bool] = False
    message: str

# Usage — logical_id is always required
event = HelloWorldEvent(logical_id=uuid4(), message="Hello!")
```

Rules:

- All messages are frozen Pydantic DTOs (`extra="allow"` for forward compatibility — old consumers silently accept new fields)
- Every concrete message class must define `code: ClassVar[int]` with a unique integer and `persistent: ClassVar[bool]`
- Always pass `logical_id=uuid4()` when constructing messages
- Message classes live in `messaging_contracts/v1/` (versioned subdirectory)
- New message modules must be imported in `messaging_contracts/__init__.py` to trigger registration

### Versioning

Messages use schema evolution within a version folder. `extra="allow"` enables forward compatibility — old consumers silently accept unknown fields from newer publishers.

- **Add field:** make it `Optional` with `Field(default=None)`, patch in handler if needed, remove optionality after all old messages drain (TTL = 7 days)
- **Remove field:** remove from consumer first, then publisher. `extra="allow"` handles the extra field during transition
- **Rename field:** = add new + remove old
- **Completely new schema:** create new message class with new code (e.g., `UserUpdatedPersonalInfoV2`), place handler in `v2/` folder. Old v1 handler stays until all v1 messages drain

## Topology

One fanout exchange per message type. Exchange name = `msg-{code}`. One queue per consuming service. All exchanges and queues are **durable** (`durable=True`) — definitions survive broker restart. FastStream defaults `durable` to `False`, so always set it explicitly.

```python
# rabbitmq_topology/resources.py
HELLO_WORLD_EVENT_EXCHANGE = RabbitExchange(
    name=get_exchange_name(message_class=HelloWorldEvent),
    type=ExchangeType.FANOUT,
    durable=True,
)

HELLO_WORLD_DLQ = RabbitQueue(
    name="hello-world.dlq",
    durable=True,
    arguments={"x-message-ttl": SEVEN_DAYS_IN_MS},
)

HELLO_WORLD_QUEUE = RabbitQueue(
    name="hello-world",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "",
        "x-dead-letter-routing-key": HELLO_WORLD_DLQ.name,
        "x-message-ttl": THREE_DAYS_IN_MS,
    },
)

BINDINGS: list[RabbitBinding] = [
    RabbitBinding(exchange=HELLO_WORLD_EVENT_EXCHANGE, queues=[HELLO_WORLD_QUEUE]),
]
```

Apply topology locally: `RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply`

All operations are **idempotent**. Adding `arguments` or changing `durable` on existing queues/exchanges requires deleting and recreating them (these properties are immutable after declaration).

## Publishing

Always use the `publish()` helper — never call `broker.publish()` directly:

```python
from libs.faststream_ext import publish

event = HelloWorldEvent(logical_id=uuid4(), message="Hello!")
await publish(broker=faststream_broker, message=event)
```

`publish()` automatically looks up the exchange via `get_exchange_for_message()`, propagates `X-Request-ID` from ContextVar, sets `persist=message.persistent` (RabbitMQ `delivery_mode`), and publishes once to the exchange. Retry republishing (`publish_to_delayed_retry_queue`) reads `delivery_mode` from the incoming `raw_message` to preserve the original persistence setting.

### Publisher-Only Services (e.g., api_gateway)

No `AsgiFastStream` needed. Bare broker connected in FastAPI lifespan:

```python
# <service>/messaging/main.py
broker = RabbitBroker(url=settings.rabbitmq_url)

# <service>/http/main.py — connect/disconnect in lifespan
await faststream_broker.connect()
yield
await faststream_broker.stop()
```

## Subscribing

```python
from faststream import AckPolicy
from faststream.rabbit import RabbitQueue, RabbitRouter
from libs.faststream_ext import message_type_filter
from messaging_contracts.v1.events import HelloWorldEvent
from rabbitmq_topology.resources import HELLO_WORLD_QUEUE

router = RabbitRouter()
_QUEUE = RabbitQueue(name=HELLO_WORLD_QUEUE.name, declare=False)
subscriber = router.subscriber(queue=_QUEUE, ack_policy=AckPolicy.ACK)

@subscriber(filter=message_type_filter(HelloWorldEvent))
async def handle_hello_world_event(body: HelloWorldEvent) -> None:
    async with Session() as session, session.begin():
        try:
            await ProcessedMessageRepository.save(
                session=session, logical_id=body.logical_id, message_code=body.code,
            )
        except IntegrityError as exc:
            raise DuplicateMessageError from exc
        # Business logic here — runs inside the same transaction
```

Rules:

- `RabbitRouter()` in `v1/handlers.py`, included via `broker.include_router(v1_router)` in `main.py`
- `declare=False` — fail-fast if topology Job hasn't run
- `ack_policy=AckPolicy.ACK` — always ack (overrides FastStream default `REJECT_ON_ERROR`)
- `message_type_filter(MessageClass)` reads `code` from body for type discrimination
- Multiple handlers can share one subscriber (different message types on the same queue)
- **Zero knowledge of exchanges or bindings** in consumer code

## Idempotent Handlers

Every handler must be idempotent. `ProcessedMessage` table (unique on `(logical_id, message_code)`) ensures each message is processed exactly once. The composite key allows a retryable handler to publish downstream events with the same `logical_id` — they won't conflict because different message types have different `code` values.

- `ProcessedMessageRepository.save(session, logical_id, message_code)` **must** be the first operation inside the transaction
- Pass `message_code=body.code` to extract the numeric code from the message class
- `IntegrityError` → `DuplicateMessageError` (passed through by `@retry()`, never retried)
- `ack_policy=AckPolicy.ACK` means duplicates are acked (no redelivery loop)

## Worker Setup

```python
from faststream.rabbit import RabbitBroker
from faststream.rabbit.prometheus import RabbitPrometheusMiddleware

_registry = CollectorRegistry()
broker = RabbitBroker(
    url=settings.rabbitmq_url,
    graceful_timeout=settings.faststream_graceful_timeout,
    middlewares=[RabbitPrometheusMiddleware(registry=_registry), RequestIdMiddleware, TimeLimitMiddleware],
)
broker.include_router(v1_router)

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
class Settings(SentrySettingsMixin, FaststreamSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(_BASE_DIR / "env.yaml"), extra="ignore")
```

| Setting                       | Type    | Default  | Purpose                                        |
| ----------------------------- | ------- | -------- | ---------------------------------------------- |
| `rabbitmq_url`                | `str`   | required | RabbitMQ AMQP connection URL                   |
| `faststream_graceful_timeout` | `float` | `65.0`   | Broker wait for in-flight messages on shutdown |

## Conventions

| Rule                 | Detail                                                                                    |
| -------------------- | ----------------------------------------------------------------------------------------- |
| Message base class   | Inherit `Event` or `AsyncCommand`, never `BaseMessage` directly                           |
| Exchange naming      | `msg-{code}` via `get_exchange_name()`                                                    |
| Exchange type        | Always `FANOUT`                                                                           |
| Durability           | Always `durable=True` on exchanges and queues (FastStream defaults to `False`)            |
| Topology management  | Centralized in `rabbitmq_topology/resources.py`, applied by k8s Job                        |
| Publishing           | Always `publish(broker, message)`, never `broker.publish()` directly                      |
| Ack policy           | Always `ack_policy=AckPolicy.ACK` on subscriber                                           |
| DLQ naming           | `<queue-name>.dlq`                                                                        |
| Retry queue naming   | `<queue-name>.delayed-retry`                                                              |
| Consumer queue       | `declare=False` — fail-fast if topology not applied                                       |
| Type discrimination  | `message_type_filter(MessageClass)` reads `code` from body                                |
| Router pattern       | `RabbitRouter()` in `v1/handlers.py`, included via `broker.include_router(v1_router)`    |
| Worker command       | `uvicorn <service>.messaging.main:app --host 0.0.0.0 --port 8001 --workers 1`             |
| Worker deployment    | `<service>-messaging` on port 8001 (HTTP uses 8000)                                       |
| Scale strategy       | Horizontal via k8s replicas, not uvicorn workers                                          |
| Idempotent handlers  | `ProcessedMessageRepository.save(session, logical_id, message_code)` first in transaction |
| Message persistence  | `persistent: ClassVar[bool]` — `True` for critical data, `False` for ephemeral/debug     |
| Message `logical_id` | Always `logical_id=uuid4()` — required field on all messages                              |
| RabbitMQ secret      | Centralized `rabbitmq-auth` ExternalSecret, referenced via `secretKeyRef`                 |

## Detailed Reference

- Retry & DLQ patterns: See [retry-dlq.md](references/retry-dlq.md)
- Testing patterns: See [testing.md](references/testing.md)
- Step-by-step guides: See [guides.md](references/guides.md)
- Kubernetes deployment: See [k8s_deployment.md](references/k8s_deployment.md)
