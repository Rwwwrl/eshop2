from messaging_contracts.common import AsyncCommand


class HelloWorldAsyncCommand(AsyncCommand):
    greeting: str
