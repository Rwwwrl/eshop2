import logging

from fastapi import FastAPI
from libs.common.enums import ServiceNameEnum
from libs.fastapi_ext.middlewares import (
    RequestIdMiddleware,
    RequestResponseLoggingMiddleware,
    UnhandledExceptionMiddleware,
)
from libs.logging import setup_logging
from libs.logging.enums import ProcessTypeEnum

from hello_world.routes import router
from hello_world.settings import settings

setup_logging(settings=settings, service_name=ServiceNameEnum.HELLO_WORLD, process_type=ProcessTypeEnum.FASTAPI)

logger = logging.getLogger(__name__)

app = FastAPI(title="Hello World Service")

app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.add_middleware(RequestIdMiddleware)
app.include_router(router=router)

logger.info("Hello World service started")
