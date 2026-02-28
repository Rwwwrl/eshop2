from logging import getLogger
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

_logger = getLogger(__name__)


def get_class_full_path(cls: type) -> str:
    return f"{cls.__module__}.{cls.__qualname__}"


# NOTE @sosov: Placeholder for real business logic. Replace with actual domain operations.
async def execute_business_logic(session: AsyncSession, **kwargs: Any) -> None:
    _logger.info("Processing message: %s", kwargs)
