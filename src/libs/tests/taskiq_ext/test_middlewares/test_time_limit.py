from libs.taskiq_ext.middlewares import TimeLimitMiddleware
from tests.taskiq_ext.test_middlewares.utils import make_message


def test_sets_default_timeout_when_missing() -> None:
    middleware = TimeLimitMiddleware(default_timeout_seconds=60)
    message = make_message()

    result = middleware.pre_execute(message=message)

    assert result.labels["timeout"] == 60


def test_preserves_explicit_timeout() -> None:
    middleware = TimeLimitMiddleware(default_timeout_seconds=60)
    message = make_message(labels={"timeout": 120})

    result = middleware.pre_execute(message=message)

    assert result.labels["timeout"] == 120
