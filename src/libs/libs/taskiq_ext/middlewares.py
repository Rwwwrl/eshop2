from datetime import timedelta
from logging import getLogger
from typing import Any

from taskiq.abc.middleware import TaskiqMiddleware
from taskiq.kicker import AsyncKicker
from taskiq.message import TaskiqMessage
from taskiq.result import TaskiqResult

from libs.datetime_ext.utils import utc_now

_logger = getLogger(__name__)

_LABELS_TO_STRIP = frozenset({"_retries", "_dlq_queue_name", "_dlq_ttl_seconds", "retry_on_error", "max_retries"})


class DeadLetterMiddleware(TaskiqMiddleware):
    async def on_error(self, message: TaskiqMessage, result: TaskiqResult[Any], exception: BaseException) -> None:
        # NOTE @sosov: Tasks without @dlq decorator have no _dlq_queue_name label — skip them.
        dlq_queue = message.labels.get("_dlq_queue_name")
        if not dlq_queue:
            return

        # NOTE @sosov: When retries are enabled, SmartRetryMiddleware handles re-queuing until
        # max_retries is exhausted. We only route to DLQ once all retries are spent.
        retry_on_error = message.labels.get("retry_on_error")
        if retry_on_error:
            retries = int(message.labels.get("_retries", 0)) + 1
            max_retries = int(message.labels["max_retries"])
            if retries < max_retries:
                return

        # NOTE @sosov: Build a clean message for the DLQ stream. Retry/DLQ config labels are
        # stripped so the DLQ message won't be re-routed if it fails again (no DLQ-to-DLQ chaining).
        ttl_seconds = int(message.labels["_dlq_ttl_seconds"])
        expires_at = utc_now() + timedelta(seconds=ttl_seconds)

        clean_labels = {k: v for k, v in message.labels.items() if k not in _LABELS_TO_STRIP}
        clean_labels["queue_name"] = dlq_queue
        clean_labels["_dlq_expires_at"] = expires_at.isoformat()

        await AsyncKicker(task_name=message.task_name, broker=self.broker, labels=clean_labels).kiq(
            *message.args, **message.kwargs
        )

        _logger.info(
            "Task %s (ID: %s) routed to DLQ %r (expires: %s)",
            message.task_name,
            message.task_id,
            dlq_queue,
            expires_at.isoformat(),
        )


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
