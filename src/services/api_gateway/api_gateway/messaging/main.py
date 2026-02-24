from faststream.redis import RedisBroker

from api_gateway.settings import settings

broker = RedisBroker(url=settings.faststream_redis_url)
