import logging
from pathlib import Path

from fastapi import FastAPI

from wearables.routes import router

VERSION_FILE = Path(__file__).parent.parent / "VERSION"
VERSION = VERSION_FILE.read_text().strip()

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Wearables Service",
    version=VERSION,
    description="Wearable data webhook ingestion service.",
)

app.include_router(router=router)
