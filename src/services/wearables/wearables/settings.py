from pathlib import Path

from libs.settings import BaseAppSettings
from libs.sqlmodel_ext.settings import PostgresSettingsMixin
from pydantic_settings import SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(PostgresSettingsMixin, BaseAppSettings):
    model_config = SettingsConfigDict(
        yaml_file=str(BASE_DIR / "env.yaml"),
        extra="ignore",
    )


settings = Settings()
