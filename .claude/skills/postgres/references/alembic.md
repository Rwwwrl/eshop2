# Alembic Reference

## Directory Structure

```
src/services/<service>/
├── alembic.ini
└── migrations/
    ├── env.py
    ├── script.py.mako
    └── versions/
        └── 20260211212335_add_wearable_event_table.py
```

## Scaffolding a New Service

```bash
cd src/services/<service>
poetry run alembic init migrations
```

Then replace `migrations/env.py` with the minimal template below.

## env.py Template

```python
import <service>.models  # noqa: F401  — registers models with metadata

from libs.alembic_ext.env_helpers import run_async_alembic
from libs.sqlmodel_ext import BaseSqlModel
from <service>.settings import settings

run_async_alembic(settings_url=settings.postgres_db_url, target_metadata=BaseSqlModel.metadata)
```

The model import is critical — without it, `BaseSqlModel.metadata` has no tables and autogenerate produces empty migrations.

## alembic.ini Key Settings

```ini
script_location = %(here)s/migrations
file_template = %%(year)d%%(month).2d%%(day).2d%%(hour).2d%%(minute).2d%%(second).2d_%%(slug)s
prepend_sys_path = .
# sqlalchemy.url is NOT set here — loaded from service settings
```

File template produces timestamp-based names: `20260211212335_add_wearable_event_table.py`.

## Commands

```bash
cd src/services/<service>

# Create migration (autogenerate from model changes)
poetry run alembic revision --autogenerate -m "description"

# Apply all migrations
poetry run alembic upgrade head

# Show current revision
poetry run alembic current

# Rollback one step
poetry run alembic downgrade -1
```

## Adding a New Model

1. Create model in `src/services/<service>/<service>/<context>/models.py`
2. Import in `migrations/env.py` so `BaseSqlModel.metadata` is populated
3. Run `poetry run alembic revision --autogenerate -m "description"`
4. Review the generated migration before applying
