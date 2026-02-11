# TimescaleDB Reference

## Available Operations

```python
from libs.alembic_ext.timescale_ops import (
    ChunkIntervalEnum,      # ONE_DAY, SEVEN_DAYS, FOURTEEN_DAYS, ONE_MONTH
    CompressAfterEnum,       # ONE_DAY, THREE_DAYS, SEVEN_DAYS, FOURTEEN_DAYS, THIRTY_DAYS, SIXTY_DAYS, NINETY_DAYS
    create_hypertable,
    set_compression,
    add_compression_policy,
)
```

## Migration Example

Call TimescaleDB ops **after** `op.create_table` in the `upgrade()` function:

```python
from libs.alembic_ext.timescale_ops import (
    ChunkIntervalEnum,
    CompressAfterEnum,
    add_compression_policy,
    create_hypertable,
    set_compression,
)


def upgrade() -> None:
    op.create_table(
        "wearable_event",
        sa.Column("id", sa.Integer, sa.Identity(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("biomarker_name", sa.String, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", "timestamp"),
    )
    op.create_index("ix_wearable_event_timestamp", "wearable_event", ["timestamp"])

    create_hypertable(
        table_name="wearable_event",
        time_column="timestamp",
        chunk_interval=ChunkIntervalEnum.ONE_DAY,
    )
    set_compression(
        table_name="wearable_event",
        segment_by="user_id",
        order_by="timestamp DESC",
    )
    add_compression_policy(
        table_name="wearable_event",
        compress_after=CompressAfterEnum.SEVEN_DAYS,
    )


def downgrade() -> None:
    op.drop_index("ix_wearable_event_timestamp", table_name="wearable_event")
    op.drop_table("wearable_event")
```

## Guidelines

- `chunk_interval <= compress_after`
- `segment_by`: columns you filter by (e.g., `user_id`)
- `order_by`: include time column with direction (e.g., `"timestamp DESC"`)
- Hypertable requires the time column in the primary key (composite PK)
- Downgrade only needs `drop_table` — dropping the table cleans up hypertable metadata

## Model Requirements

TimescaleDB hypertable models must have:

1. Composite PK including the time column: `PrimaryKeyConstraint("id", "timestamp")`
2. Explicit time column index: `Index("ix_<table>_timestamp", "timestamp")`
3. `id` with `Column(Integer, Identity())` for auto-increment

## Docker Compose

Local development uses `timescale/timescaledb:latest-pg17` on port `15432`.
