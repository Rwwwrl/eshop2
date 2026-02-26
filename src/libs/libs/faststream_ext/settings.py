from pydantic_settings import BaseSettings


class FaststreamSettingsMixin(BaseSettings):
    faststream_rabbitmq_url: str
    faststream_graceful_timeout: float = 65.0
