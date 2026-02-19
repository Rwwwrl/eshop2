import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from libs.taskiq_ext.middlewares import DeadLetterMiddleware, TaskLifecycleLogMiddleware, TimeLimitMiddleware
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


def _make_dlq_middleware() -> DeadLetterMiddleware:
    middleware = DeadLetterMiddleware()
    middleware.set_broker(broker=MagicMock())
    return middleware


_DLQ_LABELS = {
    "_dlq_queue_name": "test:dlq",
    "_dlq_ttl_seconds": 3600,
    "retry_on_error": True,
    "max_retries": 3,
}

_EXCEPTION = RuntimeError("boom")


@pytest.mark.anyio
async def test_dlq_middleware_skips_when_no_dlq_label():
    middleware = _make_dlq_middleware()
    message = _make_message(labels={"retry_on_error": True, "max_retries": 3})
    result = _make_result(is_err=True, error=_EXCEPTION)

    with patch("libs.taskiq_ext.middlewares.AsyncKicker") as mock_kicker:
        await middleware.on_error(message=message, result=result, exception=_EXCEPTION)

    mock_kicker.assert_not_called()


@pytest.mark.anyio
async def test_dlq_middleware_skips_when_retries_remaining():
    middleware = _make_dlq_middleware()
    message = _make_message(labels={**_DLQ_LABELS, "_retries": "0"})
    result = _make_result(is_err=True, error=_EXCEPTION)

    with patch("libs.taskiq_ext.middlewares.AsyncKicker") as mock_kicker:
        await middleware.on_error(message=message, result=result, exception=_EXCEPTION)

    mock_kicker.assert_not_called()


@pytest.mark.anyio
async def test_dlq_middleware_routes_on_retries_exhausted():
    middleware = _make_dlq_middleware()
    message = _make_message(labels={**_DLQ_LABELS, "_retries": "2"})
    result = _make_result(is_err=True, error=_EXCEPTION)

    mock_kiq = AsyncMock()
    with patch("libs.taskiq_ext.middlewares.AsyncKicker") as mock_kicker:
        mock_kicker.return_value.kiq = mock_kiq
        await middleware.on_error(message=message, result=result, exception=_EXCEPTION)

    mock_kicker.assert_called_once()
    mock_kiq.assert_awaited_once()


@pytest.mark.anyio
async def test_dlq_middleware_routes_immediately_when_no_retry_configured():
    middleware = _make_dlq_middleware()
    labels = {"_dlq_queue_name": "test:dlq", "_dlq_ttl_seconds": 3600}
    message = _make_message(labels=labels)
    result = _make_result(is_err=True, error=_EXCEPTION)

    mock_kiq = AsyncMock()
    with patch("libs.taskiq_ext.middlewares.AsyncKicker") as mock_kicker:
        mock_kicker.return_value.kiq = mock_kiq
        await middleware.on_error(message=message, result=result, exception=_EXCEPTION)

    mock_kicker.assert_called_once()
    mock_kiq.assert_awaited_once()


@pytest.mark.anyio
async def test_dlq_middleware_strips_retry_and_dlq_labels():
    middleware = _make_dlq_middleware()
    message = _make_message(labels={**_DLQ_LABELS, "_retries": "2", "custom": "keep"})
    result = _make_result(is_err=True, error=_EXCEPTION)

    mock_kiq = AsyncMock()
    with patch("libs.taskiq_ext.middlewares.AsyncKicker") as mock_kicker:
        mock_kicker.return_value.kiq = mock_kiq
        await middleware.on_error(message=message, result=result, exception=_EXCEPTION)

    call_kwargs = mock_kicker.call_args.kwargs
    labels = call_kwargs["labels"]
    assert "_retries" not in labels
    assert "_dlq_queue_name" not in labels
    assert "_dlq_ttl_seconds" not in labels
    assert "retry_on_error" not in labels
    assert "max_retries" not in labels


@pytest.mark.anyio
async def test_dlq_middleware_sets_expires_at_from_ttl():
    middleware = _make_dlq_middleware()
    message = _make_message(labels={**_DLQ_LABELS, "_retries": "2"})
    result = _make_result(is_err=True, error=_EXCEPTION)

    mock_kiq = AsyncMock()
    with patch("libs.taskiq_ext.middlewares.AsyncKicker") as mock_kicker:
        mock_kicker.return_value.kiq = mock_kiq
        await middleware.on_error(message=message, result=result, exception=_EXCEPTION)

    call_kwargs = mock_kicker.call_args.kwargs
    labels = call_kwargs["labels"]
    assert "queue_name" in labels
    assert labels["queue_name"] == "test:dlq"
    assert "_dlq_expires_at" in labels


@pytest.mark.anyio
async def test_dlq_middleware_preserves_unrelated_labels():
    middleware = _make_dlq_middleware()
    message = _make_message(labels={**_DLQ_LABELS, "_retries": "2", "custom_tag": "value", "timeout": 60})
    result = _make_result(is_err=True, error=_EXCEPTION)

    mock_kiq = AsyncMock()
    with patch("libs.taskiq_ext.middlewares.AsyncKicker") as mock_kicker:
        mock_kicker.return_value.kiq = mock_kiq
        await middleware.on_error(message=message, result=result, exception=_EXCEPTION)

    call_kwargs = mock_kicker.call_args.kwargs
    labels = call_kwargs["labels"]
    assert labels["custom_tag"] == "value"
    assert labels["timeout"] == 60
