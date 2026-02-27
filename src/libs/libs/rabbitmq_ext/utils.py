import aio_pika


async def health_check(rabbitmq_url: str) -> None:
    conn = await aio_pika.connect(url=rabbitmq_url, timeout=5)
    await conn.close()
