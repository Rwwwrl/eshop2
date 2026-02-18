import socket

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/host")
async def get_host() -> dict[str, str]:
    return {"host": socket.gethostname()}
