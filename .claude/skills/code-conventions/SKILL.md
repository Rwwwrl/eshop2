---
name: code-conventions
description: Detailed code conventions and style rules for MyEshop. Use when writing new code, reviewing code, or when unsure about import style, schema patterns, or code style. Trigger phrases include "convention", "import style", "schema import", "code style", "how to import".
---

# Code Conventions

## Schema Imports

- **Within the same context:** import the module, use `module.ClassName` — makes the origin file obvious at every usage site.
- **From another context:** import the class directly from `schemas/__init__.py` — never reach into internal files like `request_schemas.py` or `dtos.py`.
- **Exporting:** the owning context controls what is public via `schemas/__init__.py` with `__all__`.

See `references/schema_imports.md` for full examples.

## DTO Naming and Factory Method

- The **base DTO** that mirrors a database table is named `Base<TableName>DTO` (e.g., `BaseWearableEventDTO` for the `WearableEvent` model).
- It must have a `from_sqlmodel` class method that converts a SQLModel instance to the DTO via `model_dump()`:

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

- `id` is `int | None` (no default) — callers pass `None` explicitly for creation, gets populated when reading from DB.

## `__init__.py` Convention

- `__init__.py` should be **empty by default**.
- Only re-export symbols that are truly part of the module's **public API** — things used by other packages or services.
- Internal helpers, utilities, and implementation details must **NOT** be re-exported. Consumers import them directly from their source file (e.g., `from libs.datetime_ext.utils import utc_now`).
- When re-exporting, use `__all__` to make the public surface explicit.

```python
# Good — public API re-exported with __all__
# libs/sqlmodel_ext/__init__.py
from libs.sqlmodel_ext.base_model import BaseSqlModel
from libs.sqlmodel_ext.session import Session

__all__ = ("BaseSqlModel", "Session")

# Good — internal module, empty __init__.py
# libs/datetime_ext/__init__.py
# (empty)

# Bad — re-exporting internal helpers
# libs/datetime_ext/__init__.py
from libs.datetime_ext.utils import utc_now  # utc_now is internal, don't re-export
```
