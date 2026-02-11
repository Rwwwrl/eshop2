from sqlalchemy.ext.asyncio import AsyncSession

from wearables.models import WearableEvent
from wearables.schemas import dtos


class WearableEventRepository:
    @classmethod
    async def save(cls, session: AsyncSession, event: dtos.BaseWearableEventDTO) -> None:
        model = WearableEvent(
            user_id=event.user_id,
            biomarker_name=event.biomarker_name,
            value=event.value,
            timestamp=event.timestamp,
        )
        session.add(model)
        await session.flush()
