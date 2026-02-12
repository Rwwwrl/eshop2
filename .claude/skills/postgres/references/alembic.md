# Alembic Reference

## Directory Structure

Migrations use **expand/contract branches** for zero-downtime deployments.

```
src/services/<service>/
├── alembic.ini
└── migrations/
    ├── env.py
    ├── script.py.mako
    └── versions/
        ├── expand/
        │   ├── 20260212225344_initial_expand_branch.py
        │   └── 20260211212335_add_wearable_event_table.py
        └── contract/
            └── 20260212225049_initial_contract_branch.py
```

## Expand / Contract Branches

All migrations go into one of two branches:

| Branch | What goes here | Runs |
|--------|---------------|------|
| **expand** | Additive changes: `CREATE TABLE`, `ADD COLUMN`, `CREATE INDEX` | **Before** deployment |
| **contract** | Destructive changes: `DROP TABLE`, `DROP COLUMN`, `REMOVE CONSTRAINT` | **After** deployment |

This ensures the old code keeps working during rollout — expand adds what new code needs, contract removes what old code needed.

### Deployment order

```
1. expand migrations  →  2. deploy new code  →  3. contract migrations
```

K8s jobs: `<service>-postgres-expand-migration` and `<service>-postgres-contract-migration`.

## Scaffolding a New Service

```bash
cd src/services/<service>
poetry run alembic init migrations
mkdir -p migrations/versions/expand migrations/versions/contract
```

Then:
1. Replace `migrations/env.py` with the template below
2. Add `version_locations` to `alembic.ini`
3. Create initial branch migrations (see below)

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
truncate_slug_length = 40
version_locations = %(here)s/migrations/versions/expand %(here)s/migrations/versions/contract

# sqlalchemy.url is NOT set here — loaded from service settings
```

File template produces timestamp-based names: `20260211212335_add_wearable_event_table.py`.

## Initial Branch Migrations

Each branch needs an empty root migration that establishes the branch label. These are created once per service.

**Expand branch** (`versions/expand/`):

```python
"""initial expand branch"""

from typing import Sequence, Union

# NOTE @sosov: Empty migration that establishes the expand branch.
# All additive schema changes (CREATE, ADD) go here.
revision: str = "<generate>"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("expand",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

**Contract branch** (`versions/contract/`):

```python
"""initial contract branch"""

from typing import Sequence, Union

# NOTE @sosov: Empty migration that establishes the contract branch.
# All destructive schema changes (DROP, REMOVE) go here.
revision: str = "<generate>"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = ("contract",)
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
```

Generate revision IDs with: `poetry run python -c "from alembic.util import rev_id; print(rev_id())"`

## Commands

```bash
cd src/services/<service>

# Create migration on the expand branch (autogenerate from model changes)
poetry run alembic revision --autogenerate --head expand@head -m "description"

# Create migration on the contract branch (manual — destructive changes)
poetry run alembic revision --head contract@head -m "description"

# Apply expand migrations only
poetry run alembic upgrade expand@head

# Apply contract migrations only
poetry run alembic upgrade contract@head

# Apply all migrations (both branches)
poetry run alembic upgrade heads

# Show current revision(s)
poetry run alembic current

# Show history per branch
poetry run alembic history
```

## Adding a New Model

1. Create model in `src/services/<service>/<service>/<context>/models.py`
2. Import in `migrations/env.py` so `BaseSqlModel.metadata` is populated
3. Run `poetry run alembic revision --autogenerate --head expand@head -m "description"`
4. Review the generated migration before applying

## Renaming / Dropping a Column (Example)

Two-step process across deployments:

**Step 1 — Expand migration** (before deploy): add the new column, backfill data
```bash
poetry run alembic revision --autogenerate --head expand@head -m "add new_column to users"
```

**Step 2 — Contract migration** (after deploy): drop the old column
```bash
poetry run alembic revision --head contract@head -m "drop old_column from users"
# Edit the generated file manually — contract migrations are never autogenerated
```
