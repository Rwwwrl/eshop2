from pydantic_settings import BaseSettings


class TaskiqSettingsMixin(BaseSettings):
    taskiq_redis_url: str
