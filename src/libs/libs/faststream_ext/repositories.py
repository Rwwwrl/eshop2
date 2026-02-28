from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.faststream_ext.models import ProcessedMessage


class ProcessedMessageRepository:
    @classmethod
    async def save(cls, session: AsyncSession, logical_id: UUID, message_code: int) -> None:
        session.add(ProcessedMessage(logical_id=logical_id, message_code=message_code))
        await session.flush()
