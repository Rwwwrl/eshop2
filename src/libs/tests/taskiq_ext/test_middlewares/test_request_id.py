from libs.context_vars import request_id_var
from libs.taskiq_ext.middlewares import RequestIdMiddleware
from tests.taskiq_ext.test_middlewares.utils import make_message


def test_pre_send_injects_request_id_from_context_var() -> None:
    middleware = RequestIdMiddleware()
    message = make_message()
    token = request_id_var.set("abc-123")

    try:
        result = middleware.pre_send(message=message)
    finally:
        request_id_var.reset(token)

    assert result.labels["_request_id"] == "abc-123"


def test_pre_send_skips_when_no_request_id() -> None:
    middleware = RequestIdMiddleware()
    message = make_message()

    result = middleware.pre_send(message=message)

    assert "_request_id" not in result.labels


def test_pre_execute_sets_context_var_from_label() -> None:
    middleware = RequestIdMiddleware()
    message = make_message(labels={"_request_id": "abc-123"})

    middleware.pre_execute(message=message)

    assert request_id_var.get() == "abc-123"
    request_id_var.set(None)


def test_pre_execute_skips_when_no_label() -> None:
    middleware = RequestIdMiddleware()
    message = make_message()
    token = request_id_var.set("existing-id")

    try:
        middleware.pre_execute(message=message)
        assert request_id_var.get() == "existing-id"
    finally:
        request_id_var.reset(token)
