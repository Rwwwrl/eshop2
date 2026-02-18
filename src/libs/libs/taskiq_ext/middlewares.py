from taskiq.abc.middleware import TaskiqMiddleware
from taskiq.message import TaskiqMessage


class TimeLimitMiddleware(TaskiqMiddleware):
    """
    Sets a default ``timeout`` label on tasks that don't already have one.
    """

    def __init__(self, default_timeout_seconds: float) -> None:
        super().__init__()
        self._default_timeout_seconds = default_timeout_seconds

    def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        if "timeout" not in message.labels:
            message.labels["timeout"] = self._default_timeout_seconds
        return message
