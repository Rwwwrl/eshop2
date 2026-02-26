from pydantic import BaseModel, ConfigDict


class BaseMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Event(BaseMessage):
    pass


class AsyncCommand(BaseMessage):
    pass
