---
name: postgres
description: This skill should be used when the user works with PostgreSQL, TimescaleDB, SQLModel models, Alembic migrations, or async database sessions. Use when creating tables, writing migrations, defining models with hypertables. Trigger phrases include "create a migration", "add a postgres model", "timescale hypertable", "SQLModel", "alembic".
---

# PostgreSQL / TimescaleDB

## Project Structure

```
src/libs/libs/
├── datetime_ext/
│   └── utils.py            # utc_now() utility
├── sqlmodel_ext/
│   ├── base_model.py       # BaseSqlModel with created_at/updated_at
│   └── session.py          # Global async sessionmaker
└── alembic_ext/
    ├── timescale_ops.py    # Hypertable utilities
    └── env_helpers.py      # Async Alembic migration runner

src/services/<service>/
├── alembic.ini             # Alembic configuration
├── migrations/
│   ├── env.py              # Calls run_async_alembic()
│   ├── script.py.mako      # Migration template
│   └── versions/           # Migration files
└── <service>/
    ├── utils.py            # init_sqlmodel_engine()
    └── <context>/
        └── models.py       # SQLModel table definitions
```

## Model Patterns

All models inherit from `BaseSqlModel` (provides `created_at`, `updated_at`).

```python
from libs.sqlmodel_ext import BaseSqlModel

class MyModel(BaseSqlModel, table=True):
    __tablename__ = "my_table"
    ...
```

**Key patterns:**
- `DateTime(timezone=True)` for all datetime fields
- Enums must be stored as strings in DB: use `sa_type=String` (e.g., `status: StatusEnum = Field(sa_type=String)`)
- Indexes in `__table_args__` using SQLAlchemy `Index`

## Session Usage

```python
from libs.sqlmodel_ext import Session

async with Session() as session, session.begin():
    session.add(model_instance)
    await session.flush()
    # Auto-commits on success, auto-rollbacks on exception
```

## Repository Pattern

| Layer | Responsibility |
|-------|---------------|
| **Service** | Creates session, manages transaction (`begin()`) |
| **Repository** | Receives session, calls `flush()` after writes |

**Rules:**
- Repositories never create sessions or call `commit()`
- Call `flush()` after `add()` / `add_all()`
- `execute()` for UPDATE/DELETE doesn't need flush

## Alembic Migrations

```bash
just alembic-autogenerate "message"                                    # Create with autogenerate
cd src/services/wearables && poetry run alembic upgrade head           # Apply
cd src/services/wearables && poetry run alembic current                # Show current
cd src/services/wearables && poetry run alembic downgrade -1           # Rollback
```

**Adding new models:**
1. Create model in `src/services/<service>/<service>/<context>/models.py`
2. Import in `src/services/<service>/migrations/env.py` (so BaseSqlModel.metadata is populated)
3. Run `just alembic-autogenerate "description"` and review migration

## TimescaleDB Quick Reference

```python
from libs.alembic_ext.timescale_ops import (
    ChunkIntervalEnum,   # ONE_DAY, SEVEN_DAYS, FOURTEEN_DAYS, ONE_MONTH
    CompressAfterEnum,   # ONE_DAY, THREE_DAYS, SEVEN_DAYS, FOURTEEN_DAYS, THIRTY_DAYS, SIXTY_DAYS, NINETY_DAYS
    create_hypertable,
    set_compression,
    add_compression_policy,
)
```

**Guidelines:**
- `chunk_interval <= compress_after`
- `segment_by`: columns you filter by (e.g., `user_id`)
- `order_by`: include time column with direction
- Hypertable requires the time column in the primary key (composite PK)
