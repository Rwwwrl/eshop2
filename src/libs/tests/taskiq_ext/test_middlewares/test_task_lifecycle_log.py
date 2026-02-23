import logging

from libs.taskiq_ext.middlewares import TaskLifecycleLogMiddleware
from tests.taskiq_ext.test_middlewares.utils import make_message, make_result


def test_logs_info_on_success(caplog: logging.LogCaptureFixture) -> None:
    middleware = TaskLifecycleLogMiddleware()
    message = make_message()
    result = make_result()

    with caplog.at_level(logging.INFO):
        middleware.post_execute(message=message, result=result)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert "test-task" in record.message
    assert "test-id" in record.message
    assert "1.23s" in record.message
    assert "completed" in record.message


def test_logs_error_on_failure(caplog: logging.LogCaptureFixture) -> None:
    middleware = TaskLifecycleLogMiddleware()
    message = make_message()
    error = RuntimeError("something broke")
    result = make_result(is_err=True, error=error)

    with caplog.at_level(logging.ERROR):
        middleware.post_execute(message=message, result=result)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.ERROR
    assert "test-task" in record.message
    assert "test-id" in record.message
    assert "failed" in record.message
    assert "something broke" in record.message
