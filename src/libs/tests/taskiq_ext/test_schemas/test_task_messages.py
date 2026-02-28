from typing import ClassVar
from unittest.mock import patch
from uuid import uuid4

import pytest
from libs.taskiq_ext.schemas.task_messages import _TASK_MESSAGE_CODE_REGISTRY, BaseTaskMessage


class _MessageA(BaseTaskMessage):
    code: ClassVar[int] = 9000


class _MessageB(BaseTaskMessage):
    code: ClassVar[int] = 9001
    extra_field: str


def test_duplicate_code_raises_value_error() -> None:
    with patch.dict(_TASK_MESSAGE_CODE_REGISTRY, {9100: type("Existing", (), {})}):
        with pytest.raises(ValueError, match="Duplicate task message code 9100"):

            class _Duplicate(BaseTaskMessage):
                code: ClassVar[int] = 9100


def test_missing_code_raises_type_error() -> None:
    with pytest.raises(TypeError, match="must define a `code` class attribute"):

        class _NoCode(BaseTaskMessage):
            pass


def test_serialization_round_trip() -> None:
    logical_id = uuid4()
    msg = _MessageA(logical_id=logical_id)

    data = msg.model_dump(mode="json")
    assert data["code"] == 9000
    assert data["logical_id"] == str(logical_id)

    restored = _MessageA.model_validate(data)
    assert restored.logical_id == logical_id


def test_code_injected_in_output() -> None:
    msg = _MessageA(logical_id=uuid4())
    data = msg.model_dump()
    assert data["code"] == 9000


def test_code_stripped_from_input() -> None:
    logical_id = uuid4()
    msg = _MessageA.model_validate({"logical_id": logical_id, "code": 9000})
    assert msg.logical_id == logical_id


def test_extra_fields_round_trip() -> None:
    logical_id = uuid4()
    msg = _MessageB(logical_id=logical_id, extra_field="hello")

    data = msg.model_dump(mode="json")
    restored = _MessageB.model_validate(data)

    assert restored.extra_field == "hello"
    assert restored.logical_id == logical_id
