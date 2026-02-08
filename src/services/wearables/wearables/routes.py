import logging

from fastapi import APIRouter

from wearables.schemas import request_schemas

_logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/webhook")
async def handle_webhook(payload: request_schemas.JunctionWebhookPayload) -> dict[str, str]:
    _logger.info(
        "Received webhook event_type=%s user_id=%s client_user_id=%s",
        payload.event_type,
        payload.user_id,
        payload.client_user_id,
    )
    return {"status": "ok"}
