import logging

from fastapi import FastAPI
from libs.logging import setup_logging

from hello_world.routes import router
from hello_world.settings import settings

setup_logging(settings=settings)

logger = logging.getLogger(__name__)

app = FastAPI(title="Hello World Service")

app.include_router(router=router)

logger.info("Hello World service started")
