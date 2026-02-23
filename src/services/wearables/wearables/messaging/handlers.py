from logging import getLogger

from faststream.redis import RedisRouter

_logger = getLogger(__name__)

router = RedisRouter()


@router.subscriber(channel="hello")
async def foo(body: str) -> None:
    _logger.info("FastStream received message: %s", body)


@router.subscriber(channel="hello")
async def bar(body: str) -> None:
    _logger.info("FastStream received message: %s", body)
