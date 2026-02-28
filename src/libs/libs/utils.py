from logging import getLogger
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy.ext.asyncio import AsyncSession

_logger = getLogger(__name__)

_NAMESPACE = UUID("a3f1b2c4-d5e6-7890-abcd-ef1234567890")


def generate_deterministic_uuid(key: tuple) -> UUID:
    """Generate a deterministic UUID from a tuple key. Same inputs always produce the same UUID.

    Uses UUID5 (RFC 4122) which hashes namespace + name with SHA-1.

    Namespace is a fixed project-level constant. Changing it invalidates all previously generated UUIDs,
    breaking idempotency for in-flight messages. Never change it.

    Key is a tuple to support composite identifiers (e.g., (result_id,) or (client_id, result_id)).
    Converted via repr() to preserve structure — (21,) and (2, 1) produce different UUIDs.
    """
    return uuid5(_NAMESPACE, repr(key))


# NOTE @sosov: Placeholder for real business logic. Replace with actual domain operations.
async def execute_business_logic(session: AsyncSession, **kwargs: Any) -> None:
    _logger.info("Processing message: %s", kwargs)
