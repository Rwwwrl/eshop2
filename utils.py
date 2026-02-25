from messaging import Message


def get_message_class_path(message_class: type[Message]) -> str:
    return f"{message_class.__module__}.{message_class.__qualname__}"
