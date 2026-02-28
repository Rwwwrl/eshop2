from typing import ClassVar

from messaging_contracts.common import Event


class HelloWorldEvent(Event):
    code: ClassVar[int] = 1

    message: str


class OpenHealthResultReceivedEvent(Event):
    code: ClassVar[int] = 2

    result_id: int
