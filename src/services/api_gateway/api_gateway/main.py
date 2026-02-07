from importlib.metadata import version

import httpx
from fastapi import FastAPI
from libs.utils import print_hello_world

app = FastAPI(
    title="API Gateway",
    version=version("api-gateway"),
    description="Public-facing API Gateway for the e-shop platform.",
)

HELLO_WORLD_SERVICE_URL = "http://hello-world"


@app.get("/")
async def root():
    return {"message": "API Gateway"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/readiness_check")
async def readiness_check():
    return {"status": "ok"}


@app.get("/libs-hello")
async def libs_hello():
    return {"message": print_hello_world()}


@app.get("/hello-world/host")
async def get_hello_world_host():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{HELLO_WORLD_SERVICE_URL}/host")
        return response.json()
