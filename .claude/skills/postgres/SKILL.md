---
name: postgres
description: Guides PostgreSQL, TimescaleDB, SQLModel, and Alembic work in MyEshop. Use when creating models, writing migrations, defining hypertables, working with async sessions, or setting up database infrastructure. Trigger phrases include "create a migration", "add a postgres model", "timescale hypertable", "SQLModel", "alembic", "repository", "session", "database".
---

# PostgreSQL / TimescaleDB

## Quick Reference

| Component | Location | Import |
|-----------|----------|--------|
| `BaseSqlModel` | `libs/sqlmodel_ext/base_model.py` | `from libs.sqlmodel_ext import BaseSqlModel` |
| `Session` | `libs/sqlmodel_ext/session.py` | `from libs.sqlmodel_ext import Session` |
| `PostgresSettingsMixin` | `libs/sqlmodel_ext/settings.py` | `from libs.sqlmodel_ext.settings import PostgresSettingsMixin` |
| `health_check()` | `libs/sqlmodel_ext/utils.py` | `from libs.sqlmodel_ext.utils import health_check` |
| `utc_now()` | `libs/datetime_ext/utils.py` | `from libs.datetime_ext.utils import utc_now` |
| TimescaleDB ops | `libs/alembic_ext/timescale_ops.py` | See [references/timescale.md](references/timescale.md) |
| `run_alembic()` | `libs/alembic_ext/env_helpers.py` | `from libs.alembic_ext.env_helpers import run_alembic` |

## Model Pattern

All models inherit `BaseSqlModel` (provides `created_at`, `updated_at` with auto-update listener).

```python
from datetime import datetime

from sqlalchemy import Column, DateTime, Identity, Integer, PrimaryKeyConstraint
from sqlmodel import Field

from libs.sqlmodel_ext import BaseSqlModel


class WearableEvent(BaseSqlModel, table=True):
    __tablename__ = "wearable_event"
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        Index("ix_wearable_event_timestamp", "timestamp"),
    )

    id: int | None = Field(default=None, sa_column=Column(Integer, Identity()))
    timestamp: datetime = Field(sa_type=DateTime(timezone=True))
    user_id: int
    biomarker_name: str
    value: float
```

Rules:
- `DateTime(timezone=True)` for all datetime fields
- Enums stored as strings: `sa_type=String`
- Composite PK via `PrimaryKeyConstraint` in `__table_args__` — never field-level `primary_key=True`
- `id` uses `Column(Integer, Identity())` for auto-increment

## Session and Transaction

`Session` is an `async_sessionmaker(autobegin=False)` singleton. Bound in lifespan via `Session.configure(bind=engine)`.

```python
# Always explicit transaction
async with Session() as session, session.begin():
    session.add(model)
    await session.flush()
    # Auto-commits on success, auto-rollbacks on exception

# Read-only (no begin needed)
async with Session() as session:
    result = await session.execute(select(Model))
```

## Repository Pattern

Stateless classes with `@classmethod` methods. Accept `AsyncSession`, return DTOs.

```python
from sqlalchemy.ext.asyncio import AsyncSession

from wearables.models import WearableEvent
from wearables.schemas import dtos


class WearableEventRepository:
    @classmethod
    async def save(cls, session: AsyncSession, event: dtos.BaseWearableEventDTO) -> None:
        model = WearableEvent(
            user_id=event.user_id,
            biomarker_name=event.biomarker_name,
            value=event.value,
            timestamp=event.timestamp,
        )
        session.add(model)
        await session.flush()
```

Rules:
- Session passed per method (not stored in `__init__`)
- `flush()` after writes, never `commit()` — caller manages the transaction
- Model-to-DTO conversion inside the repository
- `execute()` for UPDATE/DELETE doesn't need flush

## Engine Initialization

Service-local, in `<service>/utils.py`:

```python
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def init_sqlmodel_engine(db_url: str) -> AsyncEngine:
    return create_async_engine(
        db_url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        connect_args={"command_timeout": 15},
    )
```

## Lifespan Pattern

```python
engine = init_sqlmodel_engine(db_url=settings.postgres_db_url)
Session.configure(bind=engine)
app.state.sqlmodel_engine = engine
yield
await engine.dispose()
```

## Alembic

Migrations use **expand/contract branches** for zero-downtime deployments. Expand (additive changes) runs before deploy, contract (destructive changes) runs after. See [references/alembic.md](references/alembic.md) for branch setup, commands, and scaffolding.

## TimescaleDB

See [references/timescale.md](references/timescale.md) for hypertable creation, compression, and migration examples.

## Settings

Services mix in `PostgresSettingsMixin` to get `postgres_db_url`:

```python
from libs.settings.base_settings import BaseAppSettings
from libs.sqlmodel_ext.settings import PostgresSettingsMixin


class Settings(PostgresSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(yaml_file=str(Path(__file__).resolve().parent.parent / "env.yaml"))
```

## Health Checks

- `/health` — liveness probe, no DB call
- `/readiness_check` — calls `health_check()` which runs `SELECT 1`
