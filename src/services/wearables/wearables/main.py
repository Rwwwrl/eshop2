from importlib.metadata import version

from fastapi import FastAPI
from libs.fastapi_ext.middlewares import RequestResponseLoggingMiddleware, UnhandledExceptionMiddleware
from libs.logging import setup_logging

from wearables.routes import router
from wearables.settings import settings

setup_logging(settings=settings)

app = FastAPI(
    title="Wearables Service",
    version=version("wearables"),
    description="Wearable data webhook ingestion service.",
)

app.add_middleware(UnhandledExceptionMiddleware)
app.add_middleware(RequestResponseLoggingMiddleware)
app.include_router(router=router)
