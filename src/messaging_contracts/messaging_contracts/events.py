from messaging_contracts.common import Event


class HelloWorldEvent(Event):
    message: str
