from importlib.metadata import version

from fastapi import FastAPI
from libs.fastapi_ext.middlewares import RequestResponseLoggingMiddleware
from libs.logging import setup_logging

from api_gateway.routes import router
from api_gateway.settings import settings

setup_logging(settings=settings)

app = FastAPI(
    title="API Gateway",
    version=version("api-gateway"),
    description="Public-facing API Gateway for the e-shop platform.",
)

app.add_middleware(RequestResponseLoggingMiddleware)
app.include_router(router=router)
