import socket

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@router.get("/host")
async def get_host() -> dict[str, str]:
    return {"host": socket.gethostname()}
