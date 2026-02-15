import httpx
from fastapi import APIRouter
from libs.consts import REQUEST_ID_HEADER
from libs.context_vars import request_id_var

router = APIRouter()

_HELLO_WORLD_SERVICE_URL = "http://hello-world"


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "API Gateway"}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/debug/error")
async def debug_error() -> None:
    raise RuntimeError("Test unhandled exception")


@router.get("/hello-world/host")
async def get_hello_world_host() -> dict:
    headers = {REQUEST_ID_HEADER: request_id_var.get()}
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{_HELLO_WORLD_SERVICE_URL}/host", headers=headers)
        return response.json()
