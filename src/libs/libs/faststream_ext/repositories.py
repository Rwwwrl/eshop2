from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.faststream_ext.models import ProcessedMessage


class ProcessedMessageRepository:
    @classmethod
    async def save(cls, session: AsyncSession, logical_id: UUID) -> None:
        session.add(ProcessedMessage(logical_id=logical_id))
        await session.flush()
