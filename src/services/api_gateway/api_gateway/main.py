from pathlib import Path

import httpx
from fastapi import FastAPI

VERSION_FILE = Path(__file__).parent.parent / "VERSION"
VERSION = VERSION_FILE.read_text().strip()

app = FastAPI(
    title="API Gateway",
    version=VERSION,
    description="Public-facing API Gateway for the e-shop platform.",
)

HELLO_WORLD_SERVICE_URL = "http://hello-world-service:8000"


@app.get("/")
async def root():
    return {"message": "API Gateway"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/readiness_check")
async def readiness_check():
    return {"status": "ok"}


@app.get("/hello-world/host")
async def get_hello_world_host():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{HELLO_WORLD_SERVICE_URL}/host")
        return response.json()
