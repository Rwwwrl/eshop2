import logging
import sys

from libs.common.enums import EnvironmentEnum, ServiceNameEnum
from libs.logging.enums import ProcessTypeEnum
from libs.logging.formatters import DevFormatter, GKEJsonFormatter
from libs.logging.settings import LoggingSettingsMixin


def setup_logging(settings: LoggingSettingsMixin, service_name: ServiceNameEnum, process_type: ProcessTypeEnum) -> None:
    log_level = getattr(logging, settings.log_level.value)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setLevel(log_level)

    match settings.environment:
        case EnvironmentEnum.DEV | EnvironmentEnum.CICD:
            handler.setFormatter(DevFormatter(service_name=service_name, process_type=process_type))
        case EnvironmentEnum.TEST | EnvironmentEnum.PROD:
            handler.setFormatter(GKEJsonFormatter(service_name=service_name, process_type=process_type))

    root_logger.addHandler(handler)

    # NOTE @sosov: Suppressing noisy third-party loggers to WARNING+.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
