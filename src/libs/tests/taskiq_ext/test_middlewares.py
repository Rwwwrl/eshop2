import logging

from libs.taskiq_ext.middlewares import TaskLifecycleLogMiddleware, TimeLimitMiddleware
from taskiq.message import TaskiqMessage
from taskiq.result import TaskiqResult


def _make_message(labels: dict | None = None) -> TaskiqMessage:
    return TaskiqMessage(
        task_id="test-id",
        task_name="test-task",
        labels=labels or {},
        args=[],
        kwargs={},
    )


def _make_result(is_err: bool = False, error: Exception | None = None) -> TaskiqResult:
    return TaskiqResult(
        is_err=is_err,
        log=None,
        return_value=None,
        execution_time=1.23,
        error=error,
    )


# --- TimeLimitMiddleware ---


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


# --- TaskLifecycleLogMiddleware ---


def test_logs_info_on_success(caplog: logging.LogCaptureFixture):
    middleware = TaskLifecycleLogMiddleware()
    message = _make_message()
    result = _make_result()

    with caplog.at_level(logging.INFO):
        middleware.post_execute(message=message, result=result)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert "test-task" in record.message
    assert "test-id" in record.message
    assert "1.23s" in record.message
    assert "completed" in record.message


def test_logs_error_on_failure(caplog: logging.LogCaptureFixture):
    middleware = TaskLifecycleLogMiddleware()
    message = _make_message()
    error = RuntimeError("something broke")
    result = _make_result(is_err=True, error=error)

    with caplog.at_level(logging.ERROR):
        middleware.post_execute(message=message, result=result)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.ERROR
    assert "test-task" in record.message
    assert "test-id" in record.message
    assert "failed" in record.message
    assert "something broke" in record.message
