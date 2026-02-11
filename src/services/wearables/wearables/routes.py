import logging

from fastapi import APIRouter, Response, status
from libs.sqlmodel_ext import Session
from libs.sqlmodel_ext.utils import health_check

from wearables import repositories
from wearables.schemas import dtos, request_schemas

_logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    await health_check()
    return {"status": "ok"}


@router.post("/webhook", status_code=status.HTTP_201_CREATED)
async def handle_webhook(payload: request_schemas.WebhookEventPayload) -> Response:
    event = dtos.BaseWearableEventDTO(
        id=None,
        user_id=payload.user_id,
        biomarker_name=payload.biomarker_name,
        value=payload.value,
        timestamp=payload.timestamp,
    )
    async with Session() as session, session.begin():
        await repositories.WearableEventRepository.save(session=session, event=event)
    return Response(status_code=status.HTTP_201_CREATED)
