def get_message_full_class_path(message_class: type) -> str:
    return f"{message_class.__module__}.{message_class.__qualname__}"
