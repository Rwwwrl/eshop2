from datetime import datetime, timezone
from typing import Any, ClassVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_serializer, model_validator

_MESSAGE_CODE_REGISTRY: dict[int, type] = {}

_ABSTRACT_SUBCLASS_NAMES = frozenset({"Event", "AsyncCommand"})


class BaseMessage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    code: ClassVar[int]
    persistent: ClassVar[bool]

    logical_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)

        if cls.__name__ in _ABSTRACT_SUBCLASS_NAMES:
            return

        try:
            code = cls.code
            _ = cls.persistent
        except AttributeError:
            raise TypeError(f"{cls.__qualname__} must define a `code` and `persistent` class attributes")

        if code in _MESSAGE_CODE_REGISTRY:
            existing = _MESSAGE_CODE_REGISTRY[code]
            raise ValueError(
                f"Duplicate message code {code}: {cls.__qualname__} conflicts with {existing.__qualname__}"
            )

        _MESSAGE_CODE_REGISTRY[code] = cls

    @model_validator(mode="wrap")
    @classmethod
    def _strip_code_from_input(cls, values: Any, handler: Any) -> Any:
        if isinstance(values, dict):
            values = {k: v for k, v in values.items() if k != "code"}
        return handler(values)

    @model_serializer(mode="wrap")
    def _inject_code_into_output(self, handler: Any) -> dict[str, Any]:
        data = handler(self)
        data["code"] = type(self).code
        return data


class Event(BaseMessage):
    pass


class AsyncCommand(BaseMessage):
    pass
