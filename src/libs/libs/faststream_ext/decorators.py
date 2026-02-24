from libs.faststream_ext.schemas.dtos import AsyncCommand, BaseMessage


def streams(*stream_names: str):
    """Decorator assigning stream names. Events: 1+, AsyncCommand: exactly 1. Fails on duplicates within call."""

    def decorator[T: type[BaseMessage]](cls: T) -> T:
        if not stream_names:
            raise TypeError(f"{cls.__name__}: @streams requires at least one stream name")

        if issubclass(cls, AsyncCommand) and len(stream_names) != 1:
            raise TypeError(f"{cls.__name__}: AsyncCommand must have exactly one stream, got {len(stream_names)}")

        if len(stream_names) != len(set(stream_names)):
            raise TypeError(f"{cls.__name__}: duplicate stream names in @streams")

        cls.__streams__ = tuple(stream_names)
        return cls

    return decorator
