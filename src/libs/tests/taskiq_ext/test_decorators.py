import inspect
from datetime import datetime, timedelta, timezone
from typing import Annotated, get_type_hints
from unittest.mock import MagicMock

import pytest
from libs.taskiq_ext.decorators import dlq
from taskiq import AsyncTaskiqDecoratedTask, Context, TaskiqDepends
from taskiq.message import TaskiqMessage


def _make_task(labels: dict | None = None) -> AsyncTaskiqDecoratedTask:
    async def _handler(context: Annotated[Context, TaskiqDepends()]) -> str:
        return "ok"

    task = MagicMock(spec=AsyncTaskiqDecoratedTask)
    task.task_name = "test-task"
    task.labels = dict(labels or {})
    task.original_func = _handler
    return task


def _make_context(labels: dict | None = None) -> Context:
    message = TaskiqMessage(
        task_id="test-id",
        task_name="test-task",
        labels=labels or {},
        args=[],
        kwargs={},
    )
    context = MagicMock(spec=Context)
    context.message = message
    return context


def test_dlq_sets_labels_on_task():
    task = _make_task(labels={"retry_on_error": True, "max_retries": 3})

    result = dlq(dlq_queue_name="test:dlq", ttl_seconds=3600)(task)

    assert result.labels["_dlq_queue_name"] == "test:dlq"
    assert result.labels["_dlq_ttl_seconds"] == 3600


def test_dlq_validates_max_retries_required():
    task = _make_task(labels={"retry_on_error": True})

    with pytest.raises(ValueError, match="max_retries"):
        dlq(dlq_queue_name="test:dlq", ttl_seconds=3600)(task)


def test_dlq_validates_context_parameter_required():
    async def _no_context_handler() -> str:
        return "ok"

    task = MagicMock(spec=AsyncTaskiqDecoratedTask)
    task.task_name = "test-task"
    task.labels = {}
    task.original_func = _no_context_handler

    with pytest.raises(TypeError, match="context"):
        dlq(dlq_queue_name="test:dlq", ttl_seconds=3600)(task)


@pytest.mark.anyio
async def test_dlq_skips_ttl_check_on_original_queue():
    task = _make_task(labels={"retry_on_error": True, "max_retries": 3})
    decorated = dlq(dlq_queue_name="test:dlq", ttl_seconds=3600)(task)

    context = _make_context(labels={})

    result = await decorated.original_func(context=context)

    assert result == "ok"


@pytest.mark.anyio
async def test_dlq_allows_fresh_dlq_message():
    task = _make_task(labels={"retry_on_error": True, "max_retries": 3})
    decorated = dlq(dlq_queue_name="test:dlq", ttl_seconds=3600)(task)

    expires_at = (datetime.now(tz=timezone.utc) + timedelta(hours=1)).isoformat()
    context = _make_context(labels={"queue_name": "test:dlq", "_dlq_expires_at": expires_at})

    result = await decorated.original_func(context=context)

    assert result == "ok"


@pytest.mark.anyio
async def test_dlq_drops_expired_message():
    task = _make_task(labels={"retry_on_error": True, "max_retries": 3})
    decorated = dlq(dlq_queue_name="test:dlq", ttl_seconds=3600)(task)

    expires_at = (datetime.now(tz=timezone.utc) - timedelta(hours=1)).isoformat()
    context = _make_context(labels={"queue_name": "test:dlq", "_dlq_expires_at": expires_at})

    result = await decorated.original_func(context=context)

    assert result is None


def test_dlq_preserves_function_signature():
    async def _handler(context: Annotated[Context, TaskiqDepends()]) -> str:
        return "ok"

    original_sig = inspect.signature(_handler)

    task = MagicMock(spec=AsyncTaskiqDecoratedTask)
    task.task_name = "test-task"
    task.labels = {"retry_on_error": True, "max_retries": 3}
    task.original_func = _handler

    decorated = dlq(dlq_queue_name="test:dlq", ttl_seconds=3600)(task)

    assert inspect.signature(decorated.original_func) == original_sig
    hints = get_type_hints(decorated.original_func, include_extras=True)
    assert "context" in hints
    assert hints["return"] is str
