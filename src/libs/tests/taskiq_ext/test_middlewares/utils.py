from taskiq.message import TaskiqMessage
from taskiq.result import TaskiqResult


def make_message(labels: dict | None = None) -> TaskiqMessage:
    return TaskiqMessage(
        task_id="test-id",
        task_name="test-task",
        labels=labels or {},
        args=[],
        kwargs={},
    )


def make_result(is_err: bool = False, error: Exception | None = None) -> TaskiqResult:
    return TaskiqResult(
        is_err=is_err,
        log=None,
        return_value=None,
        execution_time=1.23,
        error=error,
    )
