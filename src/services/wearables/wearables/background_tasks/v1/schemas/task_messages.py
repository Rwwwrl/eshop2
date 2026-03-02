from typing import ClassVar

from libs.taskiq_ext.schemas.task_messages import BaseTaskMessage


class HelloWorldTaskMessage(BaseTaskMessage):
    code: ClassVar[int] = 100
