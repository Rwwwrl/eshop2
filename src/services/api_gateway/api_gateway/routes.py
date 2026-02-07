import httpx
from fastapi import APIRouter
from libs.utils import print_hello_world

router = APIRouter()

HELLO_WORLD_SERVICE_URL = "http://hello-world"


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "API Gateway"}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/libs-hello")
async def libs_hello() -> dict[str, str]:
    return {"message": print_hello_world()}


@router.get("/hello-world/host")
async def get_hello_world_host() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{HELLO_WORLD_SERVICE_URL}/host")
        return response.json()
