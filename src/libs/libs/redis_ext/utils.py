from redis.asyncio import Redis


async def health_check(redis_url: str) -> None:
    async with Redis.from_url(redis_url, single_connection_client=True) as r:
        await r.ping()
