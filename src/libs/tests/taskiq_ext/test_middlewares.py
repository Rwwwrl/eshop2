from libs.taskiq_ext.middlewares import TimeLimitMiddleware
from taskiq.message import TaskiqMessage


def _make_message(labels: dict | None = None) -> TaskiqMessage:
    return TaskiqMessage(
        task_id="test-id",
        task_name="test-task",
        labels=labels or {},
        args=[],
        kwargs={},
    )


def test_sets_default_timeout_when_missing():
    middleware = TimeLimitMiddleware(default_timeout_seconds=60)
    message = _make_message()

    result = middleware.pre_execute(message=message)

    assert result.labels["timeout"] == 60


def test_preserves_explicit_timeout():
    middleware = TimeLimitMiddleware(default_timeout_seconds=60)
    message = _make_message(labels={"timeout": 120})

    result = middleware.pre_execute(message=message)

    assert result.labels["timeout"] == 120
