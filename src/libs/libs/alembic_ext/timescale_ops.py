from enum import Enum

from alembic import op
from sqlalchemy import text


class ChunkIntervalEnum(str, Enum):
    ONE_DAY = "1 day"
    SEVEN_DAYS = "7 days"
    FOURTEEN_DAYS = "14 days"
    ONE_MONTH = "1 month"


class CompressAfterEnum(str, Enum):
    ONE_DAY = "1 day"
    THREE_DAYS = "3 days"
    SEVEN_DAYS = "7 days"
    FOURTEEN_DAYS = "14 days"
    THIRTY_DAYS = "30 days"
    SIXTY_DAYS = "60 days"
    NINETY_DAYS = "90 days"


# NOTE @sosov: Table/column names are interpolated via f-string because PostgreSQL
# does not support bind parameters for identifiers. Safe — only called from Alembic migrations.


def create_hypertable(table_name: str, time_column: str, chunk_interval: ChunkIntervalEnum) -> None:
    op.execute(
        text(f"SELECT create_hypertable('{table_name}', by_range('{time_column}', INTERVAL :interval))").bindparams(
            interval=chunk_interval.value
        )
    )


def set_compression(table_name: str, segment_by: str, order_by: str) -> None:
    op.execute(
        text(
            f"ALTER TABLE {table_name} SET ("
            f" timescaledb.compress,"
            f" timescaledb.compress_segmentby = '{segment_by}',"
            f" timescaledb.compress_orderby = '{order_by}')"
        )
    )


def add_compression_policy(table_name: str, compress_after: CompressAfterEnum) -> None:
    op.execute(
        text(f"SELECT add_compression_policy('{table_name}', INTERVAL :interval)").bindparams(
            interval=compress_after.value
        )
    )
