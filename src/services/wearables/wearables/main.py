import logging
from importlib.metadata import version

from fastapi import FastAPI

from wearables.routes import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Wearables Service",
    version=version("wearables"),
    description="Wearable data webhook ingestion service.",
)

app.include_router(router=router)
