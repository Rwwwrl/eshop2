# Dead Letter Queue — Label Design & Execution Flow

## Label Design

### Set by `@dlq` decorator (on task registration):

| Label | Value | Purpose |
|-------|-------|---------|
| `_dlq_queue_name` | e.g., `"wearables:dlq"` | Target DLQ Redis stream name |
| `_dlq_ttl_seconds` | e.g., `604800` (7 days) | TTL for messages in the DLQ |

### Set by `DeadLetterMiddleware` (when routing to DLQ):

| Label | Value | Purpose |
|-------|-------|---------|
| `queue_name` | DLQ stream name | Broker routing — `AsyncKicker` sends to this stream |
| `_dlq_expires_at` | ISO-8601 timestamp | Absolute expiry, checked by `@dlq` wrapper at runtime |

### Stripped from DLQ message:

`_retries`, `_dlq_queue_name`, `_dlq_ttl_seconds`, `retry_on_error`, `max_retries`

Stripping `_dlq_queue_name` prevents DLQ-to-DLQ chaining. If a DLQ message fails, `DeadLetterMiddleware.on_error` checks `_dlq_queue_name` first — not present — returns immediately.

## Execution Flow

### Task fails permanently (retries exhausted):

1. Task raises exception, `_retries=2`, `max_retries=3`
2. `on_error` reversed: SmartRetry sees `2+1 >= 3` — does nothing
3. DeadLetter sees `_dlq_queue_name`, `2+1 >= 3` — routes to DLQ
4. Message lands in `wearables:dlq` stream with `_dlq_expires_at` set

### DLQ worker picks up message:

1. Worker runs same handler (same `task_name`)
2. `@dlq` wrapper: `queue_name == "wearables:dlq"` — checks `_dlq_expires_at` — not expired — runs handler

### DLQ message fails again:

1. `DeadLetterMiddleware.on_error`: `_dlq_queue_name` not in labels — returns. No re-routing. Message lost (logged by `TaskLifecycleLogMiddleware`).

### Expired DLQ message:

1. `@dlq` wrapper: `queue_name == "wearables:dlq"` — expired — logs info, returns `None`. Message acked and gone.

## Dependency Injection

`@dlq` wraps `task.original_func` with `@functools.wraps`. TaskIQ's `DependencyGraph` follows `__wrapped__` to the original function's signature, so dependency injection works unchanged. The wrapper declares `context: Context` as an explicit parameter — TaskIQ passes it as a kwarg because it resolves from the original signature.

Import-time validation ensures the original function has a `context` parameter. No runtime branching.
