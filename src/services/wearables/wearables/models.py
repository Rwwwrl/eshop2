from datetime import datetime

from libs.sqlmodel_ext import BaseSqlModel
from sqlalchemy import Column, DateTime, Identity, Index, Integer, PrimaryKeyConstraint
from sqlmodel import Field


class WearableEvent(BaseSqlModel, table=True):
    __tablename__ = "wearable_event"

    # NOTE @sosov: TimescaleDB requires the time column in the primary key.
    # ix_wearable_event_timestamp is auto-created by create_hypertable — defined
    # explicitly to keep the model in sync with the DB.
    __table_args__ = (
        PrimaryKeyConstraint("id", "timestamp"),
        Index("ix_wearable_event_timestamp", "timestamp"),
    )

    id: int | None = Field(default=None, sa_column=Column(Integer, Identity()))
    timestamp: datetime = Field(sa_type=DateTime(timezone=True))
    user_id: int
    biomarker_name: str
    value: float
