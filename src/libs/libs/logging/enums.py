from enum import Enum


class LogLevelEnum(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ProcessTypeEnum(str, Enum):
    FASTAPI = "fastapi"
    TASKIQ = "taskiq"
    FASTSTREAM = "faststream"
