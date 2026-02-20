from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def setup_fastapi_prometheus(app: FastAPI) -> None:
    Instrumentator(
        excluded_handlers=["/health", "/readiness_check", "/metrics"],
    ).instrument(app).expose(app, include_in_schema=False)
