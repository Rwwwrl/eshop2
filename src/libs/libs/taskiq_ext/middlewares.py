from logging import getLogger
from typing import Any

from taskiq.abc.middleware import TaskiqMiddleware
from taskiq.message import TaskiqMessage
from taskiq.result import TaskiqResult

_logger = getLogger(__name__)


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


class TaskLifecycleLogMiddleware(TaskiqMiddleware):
    """
    Logs task completion and failure, filling the gap left by TaskIQ's
    built-in receiver which only logs task *start*.
    """

    def post_execute(self, message: TaskiqMessage, result: TaskiqResult[Any]) -> None:
        if result.is_err:
            _logger.error(
                "Task %s (ID: %s) failed after %.2fs: %s",
                message.task_name,
                message.task_id,
                result.execution_time,
                result.error,
            )
        else:
            _logger.info(
                "Task %s (ID: %s) completed in %.2fs",
                message.task_name,
                message.task_id,
                result.execution_time,
            )
