# Schema Import Patterns

## Within the Same Context

Import the module, use `module.ClassName`:

```python
from webhooks.schemas import request_schemas

async def handle_webhook(payload: request_schemas.JunctionWebhookPayload) -> ...:
    ...
```

Bad — no locality, unclear which file defines it:

```python
from webhooks.schemas.request_schemas import JunctionWebhookPayload

async def handle_webhook(payload: JunctionWebhookPayload) -> ...:
    ...
```

## From Another Context

Import the class directly from the public API:

```python
from webhooks.schemas import JunctionWebhookPayload
```

Bad — reaching into another context's internal file:

```python
from webhooks.schemas.request_schemas import JunctionWebhookPayload
```
