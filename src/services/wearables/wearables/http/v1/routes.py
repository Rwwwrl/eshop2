from logging import getLogger

from fastapi import APIRouter, Response, status
from libs.sqlmodel_ext import Session

from wearables import repositories
from wearables.background_tasks.v1.tasks import hello_world_task
from wearables.http.v1.schemas import request_schemas
from wearables.schemas import dtos

_logger = getLogger(__name__)

router = APIRouter()


@router.post("/debug/kiq-hello-world", status_code=status.HTTP_202_ACCEPTED)
async def kiq_hello_world() -> dict[str, str]:
    _logger.info("Dispatching hello_world_task")
    result = await hello_world_task.kiq()
    _logger.info("Dispatched hello_world_task, task_id=%s", result.task_id)
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
