---
name: code-conventions
description: Enforces MyEshop code conventions for imports, schemas, DTOs, and module structure. Use when writing new code, reviewing code, or when unsure about import style, schema patterns, __init__.py exports, or DTO design. Trigger phrases include "convention", "import style", "schema import", "code style", "how to import", "DTO", "__init__".
---

# Code Conventions

## Schema Import Rules

**Within the same context** — import the module, qualify usage:

```python
from webhooks.schemas import request_schemas

async def handle_webhook(payload: request_schemas.JunctionWebhookPayload) -> ...:
    ...
```

**From another context** — import the class from the public API (`schemas/__init__.py`):

```python
from webhooks.schemas import JunctionWebhookPayload
```

**Never** reach into another context's internal files (`request_schemas.py`, `dtos.py`).

**Exporting** — the owning context controls visibility via `schemas/__init__.py` with `__all__`.

See [references/schema_imports.md](references/schema_imports.md) for full examples.

## DTO Pattern

Base DTO mirrors a database table. Named `Base<TableName>DTO`. Must have `from_sqlmodel` factory method.

```python
from datetime import datetime
from typing import Self

from libs.common.schemas.dto import DTO

from wearables.models import WearableEvent


class BaseWearableEventDTO(DTO):
    id: int | None
    user_id: int
    biomarker_name: str
    value: float
    timestamp: datetime

    @classmethod
    def from_sqlmodel(cls, model: WearableEvent) -> Self:
        return cls(**model.model_dump())
```

Rules:
- `DTO` base class: `BaseModel` with `frozen=True, extra="forbid"`
- `id` is `int | None` (no default) — callers pass `None` explicitly for creation
- Request schemas extend `BaseRequestSchema(DTO)`, response schemas extend `BaseResponseSchema(DTO)`

## `__init__.py` Convention

- Empty by default
- Only re-export symbols that are part of the module's **public API**
- Use `__all__` to make the surface explicit
- Internal helpers are imported directly from their source file

```python
# libs/sqlmodel_ext/__init__.py — public API
from libs.sqlmodel_ext.base_model import BaseSqlModel
from libs.sqlmodel_ext.session import Session

__all__ = ("BaseSqlModel", "Session")

# libs/datetime_ext/__init__.py — internal only, stays empty
# (consumers import from libs.datetime_ext.utils directly)
```

## Encapsulation

Prefix everything internal with `_`: module-level functions, classes, constants, and class attributes/methods not part of the public API.

```python
_TIMEOUT_SECONDS = 30

class _InternalHelper:
    pass

def _parse_header(raw: bytes) -> str:
    ...

class PublicService:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app  # internal state
```

## Import Ordering

Ruff isort (I001) enforced. Order: stdlib, third-party, first-party. No blank lines between groups beyond what isort expects. Run `poetry run ruff check --fix .` after writing new files.

See [references/import_ordering.md](references/import_ordering.md) for service-specific examples.
