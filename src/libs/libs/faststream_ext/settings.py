from pydantic_settings import BaseSettings


class FaststreamSettingsMixin(BaseSettings):
    faststream_redis_url: str
    faststream_max_records: int = 100
    faststream_graceful_timeout: float = 65.0
