from pydantic_settings import BaseSettings


class TaskiqSettingsMixin(BaseSettings):
    rabbitmq_url: str
    taskiq_metrics_port: int = 9090
    taskiq_health_port: int = 8081
