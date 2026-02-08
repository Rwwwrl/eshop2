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


def create_hypertable(table_name: str, time_column: str, chunk_interval: ChunkIntervalEnum) -> None:
    op.execute(
        text("SELECT create_hypertable(:table, by_range(:column, INTERVAL :interval))").bindparams(
            table=table_name, column=time_column, interval=chunk_interval.value
        )
    )


def set_compression(table_name: str, segment_by: str, order_by: str) -> None:
    op.execute(
        text(
            f"ALTER TABLE {table_name} SET ("
            f" timescaledb.compress,"
            f" timescaledb.compress_segmentby = :segment_by,"
            f" timescaledb.compress_orderby = :order_by"
            f")"
        ).bindparams(segment_by=segment_by, order_by=order_by)
    )


def add_compression_policy(table_name: str, compress_after: CompressAfterEnum) -> None:
    op.execute(
        text("SELECT add_compression_policy(:table, INTERVAL :interval)").bindparams(
            table=table_name, interval=compress_after.value
        )
    )
