from uuid import UUID

from sqlalchemy import Column, Identity, Integer, PrimaryKeyConstraint, UniqueConstraint
from sqlmodel import Field

from libs.sqlmodel_ext import BaseSqlModel


class ProcessedTaskMessage(BaseSqlModel, table=True):
    __tablename__ = "processed_task_message"
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint("logical_id", "task_message_code"),
    )

    id: int | None = Field(default=None, sa_column=Column(Integer, Identity()))
    logical_id: UUID
    task_message_code: int
