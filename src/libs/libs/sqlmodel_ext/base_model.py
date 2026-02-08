from datetime import datetime

from sqlalchemy import DateTime, event
from sqlmodel import Field, SQLModel

from libs.datetime_ext.utils import utc_now


class BaseSqlModel(SQLModel):
    """Base SQLModel class for all PostgreSQL models.

    Provides created_at and updated_at timestamp fields with automatic refresh.
    """

    created_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))
    updated_at: datetime = Field(default_factory=utc_now, sa_type=DateTime(timezone=True))


@event.listens_for(BaseSqlModel, "before_update", propagate=True)
def _set_updated_at_before_update(mapper, connection, target):
    if hasattr(target.__class__, "__table__"):
        target.updated_at = utc_now()
