from datetime import datetime
from functools import wraps
from logging import getLogger
from typing import Any

from taskiq import AsyncTaskiqDecoratedTask, Context

from libs.datetime_ext.utils import utc_now

_logger = getLogger(__name__)


def dlq(*, dlq_queue_name: str, ttl_seconds: int) -> Any:
    def decorator(task: AsyncTaskiqDecoratedTask) -> AsyncTaskiqDecoratedTask:
        if task.labels.get("retry_on_error") and "max_retries" not in task.labels:
            raise ValueError(
                f"Task {task.task_name!r} has retry_on_error=True but no max_retries. "
                "Tasks with @dlq must set max_retries explicitly."
            )

        original_func = task.original_func
        annotations = getattr(original_func, "__annotations__", {})
        if "context" not in annotations:
            raise TypeError(
                f"Task {task.task_name!r} must declare a 'context' parameter. "
                "Tasks with @dlq require `context: Annotated[Context, TaskiqDepends()]`."
            )

        task.labels["_dlq_queue_name"] = dlq_queue_name
        task.labels["_dlq_ttl_seconds"] = ttl_seconds

        @wraps(original_func)
        async def _wrapper(*args: Any, context: Context, **kwargs: Any) -> Any:
            # NOTE @sosov: If message came from the DLQ stream, check TTL before running the handler.
            if context.message.labels.get("queue_name") == dlq_queue_name:
                expires_at_raw = context.message.labels.get("_dlq_expires_at")
                if expires_at_raw:
                    expires_at = datetime.fromisoformat(expires_at_raw)
                    if utc_now() >= expires_at:
                        _logger.info(
                            "DLQ message expired for task %s (ID: %s), dropping",
                            context.message.task_name,
                            context.message.task_id,
                        )
                        return None

            return await original_func(*args, context=context, **kwargs)

        task.original_func = _wrapper

        return task

    return decorator
