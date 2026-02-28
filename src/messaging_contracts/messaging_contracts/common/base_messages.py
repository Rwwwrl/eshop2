from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BaseMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    logical_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class Event(BaseMessage):
    pass


class AsyncCommand(BaseMessage):
    pass
