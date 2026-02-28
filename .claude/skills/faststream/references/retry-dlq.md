# Retry & Dead Letter Queue (DLQ)

## Dead Letter Queue

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

### Adding Retry to a New Queue

1. Add delayed-retry queue in `rabbitmq_topology/entities.py`
2. Add to `DELAYED_RETRY_QUEUES` list
3. Apply topology: `RABBITMQ_URL=amqp://guest:guest@localhost:15672/ poetry run python -m rabbitmq_topology.apply`
4. Add `@retry(max_attempts=..., countdown=...)` to handlers
5. Add `context: ContextRepoDep` parameter to the handler function

## Retry vs DLQ Decision Table

| Decorator | Purpose | After exhaustion |
|-----------|---------|------------------|
| `@dlq()` | Immediate DLQ on first failure | N/A — no retry |
| `@retry(dlq=False)` | Retry N times, then re-raise | Exception propagates, `ack_policy` decides |
| `@retry(dlq=True)` | Retry N times, then DLQ | `NackMessage(requeue=False)` → DLQ via DLX |

Use `@retry(dlq=True)` when you want both retry and DLQ. Don't stack `@dlq()` on top of `@retry()`.
