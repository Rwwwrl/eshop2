import logging
import sys

from libs.common.enums import EnvironmentEnum
from libs.logging.formatters import DevFormatter, GKEJsonFormatter
from libs.logging.settings import LoggingSettingsMixin


def setup_logging(settings: LoggingSettingsMixin) -> None:
    log_level = getattr(logging, settings.log_level.value)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(log_level)

    match settings.environment:
        case EnvironmentEnum.DEV:
            handler.setFormatter(DevFormatter())
        case EnvironmentEnum.TEST:
            handler.setFormatter(GKEJsonFormatter())
        case _:
            raise ValueError(f"Unknown environment: {settings.environment}")

    root_logger.addHandler(handler)

    # NOTE @sosov: Suppressing noisy third-party loggers to WARNING+.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
