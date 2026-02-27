from messaging_contracts.common import Event


class HelloWorldEvent(Event):
    message: str


class OpenHealthResultReceivedEvent(Event):
    result_id: int
