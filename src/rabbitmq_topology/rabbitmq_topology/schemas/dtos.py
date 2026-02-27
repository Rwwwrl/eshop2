from faststream.rabbit import RabbitExchange, RabbitQueue
from pydantic import BaseModel, ConfigDict


class RabbitBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    exchange: RabbitExchange
    queues: list[RabbitQueue]
