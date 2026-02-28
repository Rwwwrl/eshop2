from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.taskiq_ext.models import ProcessedTaskMessage


class ProcessedTaskMessageRepository:
    @classmethod
    async def save(cls, session: AsyncSession, logical_id: UUID, task_message_code: int) -> None:
        session.add(ProcessedTaskMessage(logical_id=logical_id, task_message_code=task_message_code))
        await session.flush()
