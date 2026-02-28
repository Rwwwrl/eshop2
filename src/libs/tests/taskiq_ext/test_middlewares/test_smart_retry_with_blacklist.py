from unittest.mock import AsyncMock, patch

import pytest
from libs.taskiq_ext.exceptions import DuplicateTaskMessageError
from libs.taskiq_ext.middlewares import SmartRetryWithBlacklistMiddleware
from tests.taskiq_ext.test_middlewares.utils import make_message, make_result


@pytest.mark.asyncio(loop_scope="session")
async def test_skips_retry_on_duplicate_task_message_error() -> None:
    middleware = SmartRetryWithBlacklistMiddleware(use_jitter=True)
    message = make_message(labels={"retry_on_error": "true", "max_retries": "3"})
    result = make_result(is_err=True)
    exception = DuplicateTaskMessageError("duplicate")

    await middleware.on_error(message=message, result=result, exception=exception)

    # If it returned early (didn't call super), no retry was scheduled.
    # Verify by checking labels — _retries should NOT be set.
    assert "_retries" not in message.labels


@pytest.mark.asyncio(loop_scope="session")
async def test_delegates_to_super_on_other_exceptions() -> None:
    middleware = SmartRetryWithBlacklistMiddleware(use_jitter=True)
    message = make_message(labels={"retry_on_error": "true", "max_retries": "3"})
    result = make_result(is_err=True)
    exception = RuntimeError("transient failure")

    with patch(
        "taskiq.middlewares.smart_retry_middleware.SmartRetryMiddleware.on_error",
        new_callable=AsyncMock,
    ) as mock_super_on_error:
        await middleware.on_error(message=message, result=result, exception=exception)
        mock_super_on_error.assert_called_once_with(message=message, result=result, exception=exception)
