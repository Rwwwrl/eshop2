from fastapi import APIRouter, Response, status
from libs.redis_ext.utils import health_check as redis_health_check
from libs.sqlmodel_ext import Session
from libs.sqlmodel_ext.utils import health_check as postgres_health_check

from wearables import repositories
from wearables.http.schemas import request_schemas
from wearables.messaging.handlers import hello_world_task
from wearables.schemas import dtos
from wearables.settings import settings

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readiness_check")
async def readiness_check() -> dict[str, str]:
    await postgres_health_check()
    await redis_health_check(redis_url=settings.taskiq_redis_url)
    return {"status": "ok"}


@router.post("/debug/kiq-hello-world", status_code=status.HTTP_202_ACCEPTED)
async def kiq_hello_world() -> dict[str, str]:
    result = await hello_world_task.kiq()
    return {"task_id": result.task_id}


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
