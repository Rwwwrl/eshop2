from typing import ClassVar

from libs.common.schemas.dto import DTO


class BaseMessage(DTO):
    __streams__: ClassVar[tuple[str, ...]]


class Event(BaseMessage):
    pass


class AsyncCommand(BaseMessage):
    pass
