from typing import ClassVar

from messaging_contracts.common import AsyncCommand


class HelloWorldAsyncCommand(AsyncCommand):
    code: ClassVar[int] = 3

    greeting: str
