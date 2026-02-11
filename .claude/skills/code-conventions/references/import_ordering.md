# Import Ordering Examples

Ruff isort (I001) enforces consistent import ordering across the codebase.

## Standard Pattern

```python
# 1. Standard library
from collections.abc import AsyncGenerator
from datetime import datetime

# 2. Third-party
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Column, DateTime, Identity, Integer

# 3. First-party (libs)
from libs.sqlmodel_ext import BaseSqlModel, Session

# 4. First-party (service-local)
from wearables.models import WearableEvent
from wearables.routes import router
```

## Test File Pattern

```python
# Standard library
from collections.abc import AsyncGenerator

# Third-party (pytest)
import pytest
import pytest_asyncio

# Third-party (framework)
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# First-party
from libs.sqlmodel_ext import BaseSqlModel
from wearables.models import WearableEvent
```

## Common Fix

After writing new files, blank lines between import groups may trigger I001. Fix with:

```bash
poetry run ruff check --fix .
```
