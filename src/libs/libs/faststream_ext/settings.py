from pydantic_settings import BaseSettings


class FaststreamSettingsMixin(BaseSettings):
    faststream_redis_url: str
