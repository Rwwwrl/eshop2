from enum import Enum, auto


class EnvironmentEnum(str, Enum):
    DEV = "dev"
    TEST = "test"
    CICD = "cicd"


class ServiceNameEnum(str, Enum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> str:
        return name.lower().replace("_", "-")

    API_GATEWAY = auto()
    HELLO_WORLD = auto()
    WEARABLES = auto()
