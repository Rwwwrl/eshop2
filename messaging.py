from pydantic import BaseModel


class Message(BaseModel):
    pass


class Event(Message):
    pass


class AsyncCommand(Message):
    pass


class SomeEvent1(Event):
    value1: str


class SomeEvent2(Event):
    value2: str


class SomeAsyncCommand1(AsyncCommand):
    value1: str
