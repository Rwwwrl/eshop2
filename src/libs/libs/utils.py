def get_class_full_path(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"
