from typing import ClassVar

from messaging_contracts.common import Event


class HelloWorldEvent(Event):
    code: ClassVar[int] = 1
    persistent: ClassVar[bool] = False

    message: str


class OpenHealthResultReceivedEvent(Event):
    code: ClassVar[int] = 2
    persistent: ClassVar[bool] = True

    result_id: int
