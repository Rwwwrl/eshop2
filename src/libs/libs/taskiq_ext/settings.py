from pydantic_settings import BaseSettings


class TaskiqSettingsMixin(BaseSettings):
    taskiq_redis_url: str
    taskiq_metrics_port: int = 9090
