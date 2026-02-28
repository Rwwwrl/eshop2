from uuid import UUID

from sqlalchemy import Column, Identity, Integer, PrimaryKeyConstraint, UniqueConstraint
from sqlmodel import Field

from libs.sqlmodel_ext import BaseSqlModel


class ProcessedMessage(BaseSqlModel, table=True):
    __tablename__ = "processed_message"
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint("logical_id"),
    )

    id: int | None = Field(default=None, sa_column=Column(Integer, Identity()))
    logical_id: UUID
